from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
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
        # Проверяем, фото или видео
        if photo_downloader.is_photo_url(url):
            # Это фото
            return {
                'type': 'photos',
                'redirect': '/photos'
            }
        
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
        
        # Возвращаем все фото
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
async def download_photos(image_urls: List[str] = Form(...)):
    """Скачивает выбранные фото и отдаёт ZIP-архивом"""
    try:
        # Скачиваем выбранные фото
        photo_paths = await photo_downloader.download_selected_photos(image_urls)
        
        if not photo_paths:
            return JSONResponse(
                status_code=404,
                content={"error": "Не удалось скачать фото"}
            )
        
        # Создаём ZIP
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
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )

@app.on_event("startup")
async def startup():
    # Очистка старых файлов
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
