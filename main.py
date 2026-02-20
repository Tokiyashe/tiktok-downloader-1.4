from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import shutil
import zipfile
import uuid
from typing import List

# Импортируем раздельные модули
import video_downloader
import photo_downloader

app = FastAPI(title="TikTok Downloader")
templates = Jinja2Templates(directory="templates")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем папки
os.makedirs("downloads/videos", exist_ok=True)
os.makedirs("downloads/photos", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/photos", response_class=HTMLResponse)
async def photos_page(request: Request):
    return templates.TemplateResponse("photos.html", {"request": request})

@app.post("/analyze")
async def analyze_url(url: str = Form(...)):
    """Анализирует ссылку и определяет тип контента"""
    try:
        # Разрешаем короткую ссылку если нужно
        if 'vt.tiktok.com' in url:
            url = await video_downloader.resolve_short_url(url)
        
        # Проверяем, фото или видео
        if photo_downloader.is_photo_url(url):
            return {'type': 'photos', 'redirect': '/photos'}
        
        # Проверяем видео
        video_info = video_downloader.get_video_info(url)
        if video_info.get('is_video'):
            return video_info
        
        return {'type': 'unknown', 'error': 'Не удалось определить тип контента'}
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

@app.post("/analyze/photos")
async def analyze_photos(url: str = Form(...)):
    """Анализирует ссылку и возвращает список фото для выбора"""
    try:
        photo_urls = await photo_downloader.get_photo_urls(url)
        
        if not photo_urls:
            return JSONResponse(
                status_code=404,
                content={"error": "Не найдено фото по этой ссылке"}
            )
        
        return {
            'type': 'photos',
            'images': photo_urls,
            'count': len(photo_urls),
            'title': 'TikTok Photos',
            'author': 'Unknown'
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

@app.post("/download/video")
async def download_video(url: str = Form(...)):
    """Скачивает видео"""
    try:
        # Разрешаем короткую ссылку если нужно
        if 'vt.tiktok.com' in url:
            url = await video_downloader.resolve_short_url(url)
        
        file_path = await asyncio.to_thread(video_downloader.download_video, url)
        
        if not os.path.exists(file_path):
            return JSONResponse(
                status_code=404,
                content={"error": "Видео не найдено"}
            )
            
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            filename="tiktok_video.mp4"
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

@app.post("/download/photos")
async def download_photos(image_urls: List[str] = Form(...), download_type: str = Form(...)):
    """
    Скачивает выбранные фото
    download_type: 'single' - по одному, 'zip' - архивом
    """
    try:
        # Скачиваем выбранные фото
        photo_paths = await photo_downloader.download_selected_photos(image_urls)
        
        if not photo_paths:
            return JSONResponse(
                status_code=404,
                content={"error": "Не удалось скачать фото"}
            )
        
        # Если выбран режим ZIP
        if download_type == 'zip':
            zip_filename = f"tiktok_photos_{uuid.uuid4()}.zip"
            zip_path = os.path.join("downloads/photos", zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in photo_paths:
                    zipf.write(file_path, os.path.basename(file_path))
            
            return FileResponse(
                path=zip_path,
                media_type="application/zip",
                filename="tiktok_photos.zip"
            )
        
        # Если выбран режим "по одному"
        else:
            # Если одно фото - отдаём его напрямую
            if len(photo_paths) == 1:
                filename = os.path.basename(photo_paths[0])
                return FileResponse(
                    path=photo_paths[0],
                    media_type="image/jpeg",
                    filename=filename
                )
            
            # Если несколько - возвращаем список файлов
            file_list = []
            for i, path in enumerate(photo_paths):
                filename = os.path.basename(path)
                # Копируем файл с понятным именем
                new_filename = f"tiktok_photo_{i+1}.jpg"
                new_path = os.path.join("downloads/photos", new_filename)
                shutil.copy2(path, new_path)
                file_list.append({
                    'filename': new_filename,
                    'url': f'/files/{new_filename}',
                    'original': filename
                })
            
            return {
                'type': 'multiple',
                'files': file_list,
                'count': len(file_list)
            }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

# Эндпоинт для скачивания отдельных файлов
@app.get("/files/{filename}")
async def get_file(filename: str):
    """Отдаёт файл по имени"""
    file_path = os.path.join("downloads/photos", filename)
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            media_type="image/jpeg",
            filename=filename
        )
    return JSONResponse(
        status_code=404,
        content={"error": "Файл не найден"}
    )

@app.on_event("startup")
async def startup():
    for folder in ["downloads/videos", "downloads/photos"]:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Ошибка удаления {file_path}: {e}")

@app.on_event("shutdown")
async def shutdown():
    shutil.rmtree("downloads", ignore_errors=True)
