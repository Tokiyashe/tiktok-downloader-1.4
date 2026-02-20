import os
import uuid
import asyncio
import httpx
import aiofiles
import subprocess
import json
from typing import List, Dict, Union, Optional

PHOTOS_FOLDER = "downloads/photos"
os.makedirs(PHOTOS_FOLDER, exist_ok=True)

def is_photo_url(url: str) -> bool:
    """Проверяет, что ссылка ведёт на фото/слайд-шоу"""
    return '/photo/' in url.lower()

async def get_photos_from_url(url: str) -> List[str]:
    """
    Получает ссылки на фото через gallery-dl (запускает как subprocess)
    gallery-dl отлично работает с TikTok фото
    """
    try:
        # Запускаем gallery-dl в режиме получения URLs без скачивания
        cmd = [
            'gallery-dl',
            '--get-urls',
            '--no-download',
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            print(f"gallery-dl error: {stderr.decode()}")
            return []
        
        # Парсим вывод - каждая строка это URL фото
        urls = stdout.decode().strip().split('\n')
        return [u for u in urls if u.startswith('http')]
        
    except Exception as e:
        print(f"Ошибка gallery-dl: {e}")
        return []

async def download_photos_direct(image_urls: List[str]) -> List[str]:
    """Прямое скачивание фото через HTTP (fallback)"""
    downloaded = []
    
    for i, img_url in enumerate(image_urls):
        try:
            unique_name = f"{uuid.uuid4()}.jpg"
            file_path = os.path.join(PHOTOS_FOLDER, unique_name)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(img_url, follow_redirects=True)
                if response.status_code == 200:
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(response.content)
                    downloaded.append(file_path)
                    
        except Exception as e:
            print(f"Ошибка скачивания фото {i}: {e}")
    
    return downloaded

async def download_photos(url: str) -> List[str]:
    """Основная функция скачивания фото"""
    # Сначала пробуем через gallery-dl
    photo_urls = await get_photos_from_url(url)
    
    if photo_urls:
        return await download_photos_direct(photo_urls)
    
    # Если gallery-dl не сработал, пробуем альтернативный метод
    return await download_photos_fallback(url)

async def download_photos_fallback(url: str) -> List[str]:
    """Запасной метод через анализ страницы"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            html = response.text
            
            # Ищем ссылки на изображения в HTML
            import re
            img_pattern = r'https?://[^\s"\']+\.(?:jpg|jpeg|png|webp)[^\s"\']*'
            urls = re.findall(img_pattern, html)
            
            # Убираем дубликаты
            unique_urls = list(set(urls))
            
            if unique_urls:
                return await download_photos_direct(unique_urls[:10])  # максимум 10 фото
            
    except Exception as e:
        print(f"Fallback error: {e}")
    
    return []