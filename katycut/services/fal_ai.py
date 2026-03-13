import asyncio
import base64
import logging
import httpx

from config import FAL_API_KEY, FAL_QUEUE_URL, FAL_RESULT_URL

logger = logging.getLogger(__name__)

POLL_INTERVAL = 2
MAX_POLL_ATTEMPTS = 60  # 2 minutes max


async def remove_background(image_bytes: bytes, filename: str = "image.jpg") -> bytes:
    """
    Submit image to FAL.ai bria background removal.
    Sends as base64 data URL. Returns result image bytes.
    """
    # Determine mime type
    mime = "image/jpeg"
    if filename.lower().endswith(".png"):
        mime = "image/png"
    elif filename.lower().endswith(".webp"):
        mime = "image/webp"

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{mime};base64,{b64}"

    headers = {
        "Authorization": f"Key {FAL_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(FAL_QUEUE_URL, json={"image_url": data_url}, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    request_id = data.get("request_id")
    if not request_id:
        raise RuntimeError(f"FAL.ai did not return request_id: {data}")

    logger.info(f"FAL.ai job submitted, request_id={request_id}")
    result_url = FAL_RESULT_URL.format(request_id=request_id)

    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL)
            resp = await client.get(result_url, headers=headers)

            if resp.status_code == 200:
                result = resp.json()
                image_url = _extract_image_url(result)
                if image_url:
                    logger.info(f"FAL.ai done, downloading result from {image_url}")
                    dl = await client.get(image_url)
                    dl.raise_for_status()
                    return dl.content

            elif resp.status_code == 202:
                logger.debug(f"FAL.ai still processing (attempt {attempt + 1})")
                continue
            else:
                logger.warning(f"FAL.ai poll {resp.status_code}: {resp.text}")

    raise RuntimeError("FAL.ai job timed out after 2 minutes")


def _extract_image_url(result: dict) -> str | None:
    if "image" in result and isinstance(result["image"], dict):
        return result["image"].get("url")
    if "images" in result and isinstance(result["images"], list):
        imgs = result["images"]
        if imgs and isinstance(imgs[0], dict):
            return imgs[0].get("url")
    output = result.get("output", {})
    if isinstance(output, dict):
        if "image" in output and isinstance(output["image"], dict):
            return output["image"].get("url")
        if "images" in output and isinstance(output["images"], list):
            imgs = output["images"]
            if imgs and isinstance(imgs[0], dict):
                return imgs[0].get("url")
    return None
