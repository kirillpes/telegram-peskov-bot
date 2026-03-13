import logging
import mimetypes
import httpx

from config import UPLOADTHING_SECRET, UPLOADTHING_APP_ID, UPLOADTHING_API_URL

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "x-uploadthing-api-key": UPLOADTHING_SECRET,
        "Content-Type": "application/json",
    }


async def upload_image(image_bytes: bytes, filename: str = "image.jpg") -> str:
    """
    Upload image bytes to UploadThing V7 API.
    Returns the public URL of the uploaded file.
    Raises RuntimeError on failure.
    """
    mime_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
    file_size = len(image_bytes)

    async with httpx.AsyncClient(timeout=60) as client:
        # Step 1: Request presigned URL from UploadThing
        presign_resp = await client.post(
            f"{UPLOADTHING_API_URL}/uploadFiles",
            headers=_headers(),
            json={
                "files": [
                    {
                        "name": filename,
                        "size": file_size,
                        "type": mime_type,
                    }
                ],
                "acl": "public-read",
                "contentDisposition": "inline",
            },
        )

        if presign_resp.status_code not in (200, 201):
            raise RuntimeError(
                f"UploadThing presign failed {presign_resp.status_code}: {presign_resp.text}"
            )

        presign_data = presign_resp.json()
        logger.debug(f"UploadThing presign response: {presign_data}")

        # Extract upload URL and file key from response
        file_info = _extract_file_info(presign_data)
        if not file_info:
            raise RuntimeError(f"UploadThing unexpected response structure: {presign_data}")

        upload_url = file_info["url"]
        fields = file_info.get("fields", {})
        file_url = file_info["fileUrl"]

        # Step 2: Upload file to S3 presigned URL
        if fields:
            # Multipart form upload
            form_data = {k: (None, v) for k, v in fields.items()}
            form_data["file"] = (filename, image_bytes, mime_type)
            upload_resp = await client.post(upload_url, files=form_data)
        else:
            # Direct PUT upload
            upload_resp = await client.put(
                upload_url,
                content=image_bytes,
                headers={"Content-Type": mime_type},
            )

        if upload_resp.status_code not in (200, 201, 204):
            raise RuntimeError(
                f"UploadThing S3 upload failed {upload_resp.status_code}: {upload_resp.text}"
            )

        logger.info(f"UploadThing upload success: {file_url}")
        return file_url


def _extract_file_info(response: dict | list) -> dict | None:
    """Extract upload URL, fields, and final file URL from UploadThing response."""
    # Response can be list or dict with 'data' key
    if isinstance(response, list):
        items = response
    elif isinstance(response, dict):
        items = response.get("data", [response])
    else:
        return None

    if not items:
        return None

    item = items[0] if isinstance(items, list) else items

    # UploadThing V7 response structure
    url = item.get("url") or item.get("uploadUrl") or item.get("presignedUrl")
    fields = item.get("fields", {})
    file_url = (
        item.get("fileUrl")
        or item.get("ufsUrl")
        or item.get("appUrl")
        or f"https://utfs.io/f/{item.get('key', '')}"
    )

    if not url:
        return None

    return {"url": url, "fields": fields, "fileUrl": file_url}
