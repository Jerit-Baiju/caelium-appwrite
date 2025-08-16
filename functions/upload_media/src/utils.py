import email
import io
import json
import os
from email import policy

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image

# Service account credentials from environment
SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
SCOPES = ["https://www.googleapis.com/auth/drive"]
FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")


def is_image_file(file_bytes):
    try:
        Image.open(io.BytesIO(file_bytes)).verify()
        return True
    except Exception:
        return False


def parse_multipart_data(body_binary, content_type):
    """
    Parses multipart/form-data from a binary HTTP request body.

    Args:
        body_binary (bytes): The raw binary body of the HTTP request containing multipart/form-data.
        content_type (str): The Content-Type header value, including the boundary.

    Returns:
        tuple: A tuple (form_data, files) where:
            - form_data (dict): A dictionary mapping form field names to their string values.
            - files (dict): A dictionary mapping field names to a list of files, where each file is a dict with:
                - "content" (bytes): The file content.
                - "filename" (str): The original filename from the upload.

    Example:
        form_data, files = parse_multipart_data(body, content_type)
    """

    headers = f"Content-Type: {content_type}\r\n\r\n"
    full_message = headers.encode() + body_binary

    # Parse the message
    msg = email.message_from_bytes(full_message, policy=policy.default)

    files = {}
    form_data = {}

    if msg.is_multipart():
        for part in msg.iter_parts():
            content_disposition = part.get("content-disposition", "")
            if "form-data" in content_disposition:
                # Extract the name attribute
                name = None
                filename = None
                for param in content_disposition.split(";"):
                    param = param.strip()
                    if param.startswith("name="):
                        name = param.split("=", 1)[1].strip('"')
                    elif param.startswith("filename="):
                        filename = param.split("=", 1)[1].strip('"')

                if name:
                    if filename:  # This is a file
                        # Handle multiple files with the same field name (like media[])
                        if name not in files:
                            files[name] = []
                        files[name].append(
                            {
                                "content": part.get_payload(decode=True),
                                "filename": filename,
                            }
                        )
                    else:  # This is a form field
                        content = part.get_payload(decode=True)
                        if isinstance(content, bytes):
                            content = content.decode("utf-8")
                        form_data[name] = content

    return form_data, files


def create_thumbnail(image_bytes, size=(150, 150)):
    """
    Creates a thumbnail image from the given image bytes.
    Args:
        image_bytes (bytes): The original image in bytes.
        size (tuple, optional): The desired size for the thumbnail as a (width, height) tuple. Defaults to (150, 150).
    Returns:
        bytes or None: The thumbnail image in bytes if successful, otherwise None.
    """

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img_format = img.format
            img.thumbnail(size, Image.Resampling.LANCZOS)
            output_io = io.BytesIO()
            img.save(output_io, format=img_format)
            output_io.seek(0)
            return output_io.read()
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None


def upload_file_to_drive(upload_filename: str, upload_uuid: str, file_content: bytes) -> str:
    """
    Uploads a file to Google Drive inside a newly created folder named after the given UUID.

    Args:
        upload_filename (str): The name to assign to the uploaded file in Google Drive.
        upload_uuid (str): The UUID used as the name for the new folder in which the file will be stored.
        file_content (bytes): The binary content of the file to upload.

    Returns:
        str: The file ID of the uploaded file in Google Drive.

    Raises:
        googleapiclient.errors.HttpError: If an error occurs during the upload process.
    """

    creds = service_account.Credentials.from_service_account_info(
        json.loads(SERVICE_ACCOUNT_JSON), scopes=SCOPES  # pyright: ignore[reportArgumentType]
    )
    service = build("drive", "v3", credentials=creds)

    folder_metadata = {
        "name": upload_uuid,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [FOLDER_ID],
    }
    folder_resp = service.files().create(body=folder_metadata, fields="id").execute()
    folder_id = folder_resp.get("id")

    file_metadata = {"name": upload_filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype="application/octet-stream")
    file_resp = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    drive_file_id = file_resp.get("id")
    service.permissions().create(
        fileId=drive_file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()
    # f"https://drive.google.com/uc?id={drive_file_id}&export=download"
    return drive_file_id
