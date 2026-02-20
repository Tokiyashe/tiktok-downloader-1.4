import os
import uuid
import yt_dlp
from typing import Dict, Union, Optional

DOWNLOAD_FOLDER = "downloads/videos"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def is_video_url(url: str) -> bool:
    """Проверяет, что ссылка ведёт на видео (не фото)"""
    return '/video/' in url.lower() and '/photo/' not in url.lower()

def download_video(url: str) -> str:
    """Скачивает видео из TikTok"""
    output_template = os.path.join(DOWNLOAD_FOLDER, f"%(id)s.%(ext)s")
    
    ydl_opts = {
        'outtmpl': output_template,
        'format': 'best[ext=mp4]',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
        'retries': 5,
        'fragment_retries': 5,
        'extractor_retries': 5,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if not filename.endswith('.mp4'):
                base = os.path.splitext(filename)[0]
                filename = base + '.mp4'
            
            unique_name = f"{uuid.uuid4()}.mp4"
            new_path = os.path.join(DOWNLOAD_FOLDER, unique_name)
            
            if os.path.exists(filename):
                os.rename(filename, new_path)
            else:
                for file in os.listdir(DOWNLOAD_FOLDER):
                    if file.endswith('.mp4'):
                        os.rename(os.path.join(DOWNLOAD_FOLDER, file), new_path)
                        break
            
            return new_path
            
    except Exception as e:
        raise Exception(f"Ошибка скачивания видео: {str(e)}")

def get_video_info(url: str) -> Dict[str, Union[str, bool]]:
    """Получает информацию о видео"""
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'type': 'video',
                'url': url,
                'title': info.get('title', 'TikTok Video'),
                'author': info.get('uploader', 'Unknown'),
                'duration': info.get('duration', 0),
                'is_video': True
            }
    except:
        # Если не удалось получить инфо, значит это не видео
        return {'type': 'unknown', 'is_video': False}