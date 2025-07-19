from email import policy
import io
import email
from PIL import Image


def is_image_file(file_bytes):
    try:
        Image.open(io.BytesIO(file_bytes)).verify()
        return True
    except Exception:
        return False


def parse_multipart_data(body_binary, content_type):
    """Parse multipart/form-data to extract both files and form fields"""
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
    Creates a low-resolution thumbnail from image bytes and returns thumbnail bytes.

    Args:
        image_bytes (bytes): Original image data
        size (tuple, optional): Thumbnail dimensions (width, height). Default is (150, 150)

    Returns:
        bytes: Thumbnail image data (same format as input)
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
