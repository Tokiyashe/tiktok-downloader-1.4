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
        
        # Возвращаем первые 12 фото (для скорости загрузки)
        preview_urls = photo_urls[:12]
        
        return {
            'type': 'photos',
            'images': preview_urls,
            'all_images': photo_urls,  # сохраняем все для скачивания
            'count': len(photo_urls),
            'title': 'TikTok Photos',
            'author': 'Unknown'
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
