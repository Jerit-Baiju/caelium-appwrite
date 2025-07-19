import base64

import os

import requests
from appwrite.client import Client, InputFile
from appwrite.services.storage import Storage

from . import utils


def main(context):
    client = (
        Client()
        .set_endpoint("https://fra.cloud.appwrite.io/v1")
        .set_project(os.environ["APPWRITE_FUNCTION_PROJECT_ID"])
        .set_key(context.req.headers["x-appwrite-key"])
    )

    basic_auth_user = os.environ.get("AUTH_USERNAME", "")
    basic_auth_pass = os.environ.get("AUTH_PASSWORD", "")
    basic_auth = base64.b64encode(f"{basic_auth_user}:{basic_auth_pass}".encode()).decode()
    headers = {"Authorization": f"Basic {basic_auth}"}

    if context.req.path == "/ping":
        return context.res.text("Pong")

    if context.req.method == "POST":
        # Get content type to determine how to parse the request
        content_type = context.req.headers.get("content-type", "")

        if "multipart/form-data" in content_type:
            # Parse multipart data to get both form fields and files
            form_data, files = utils.parse_multipart_data(context.req.body_binary, content_type)

            # Extract authToken from form data
            auth_token = form_data.get("authToken")
            # Prepare Basic Auth header

            response = requests.post(
                f"{os.environ['SERVER_URL']}/api/externals/verify_jwt/",
                json={"accessToken": auth_token},
                timeout=10,
                headers=headers,
            )

            # Check if server response is valid
            try:
                resp_json = response.json()
            except Exception:
                return context.res.json({"error": "Invalid response from auth server, Server may be down"}, 500)

            if resp_json.get("valid") is True:
                # Get the uploaded files under the 'media' field
                uploaded_files = files.get("media", [])

                if uploaded_files:

                    storage = Storage(client)
                    uploaded_file_ids = []
                    oversized_files = []
                    # No need to store thumbnails in response
                    max_size_bytes = 15 * 1024 * 1024  # 15 MB

                    # Process each uploaded file
                    for _, uploaded_file in enumerate(uploaded_files):
                        filename = uploaded_file["filename"]
                        file_content = uploaded_file["content"]
                        file_size = len(file_content)

                        if file_size > max_size_bytes:
                            oversized_files.append({"filename": filename, "size": file_size})
                            continue

                        # Upload each file to storage
                        f = storage.create_file(
                            os.environ["BUCKET_ID"],
                            file=InputFile.from_bytes(file_content, filename=filename),
                            file_id="unique()",
                        )
                        uploaded_file_ids.append(f["$id"])

                        # If file is an image, create a thumbnail (in-memory) and upload it
                        if utils.is_image_file(file_content):
                            thumb_bytes = utils.create_thumbnail(file_content, (300,300))
                            if thumb_bytes:
                                # Generate thumbnail filename
                                name, ext = os.path.splitext(filename)
                                thumb_filename = f"thumbnail_{name}{ext}"
                                # Upload thumbnail to storage
                                storage.create_file(
                                    os.environ["BUCKET_ID"],
                                    file=InputFile.from_bytes(thumb_bytes, filename=thumb_filename),
                                    file_id="unique()",
                                )

                    # Return the list of uploaded file IDs and any oversized files (no thumbnails in response)
                    response = {
                        "success": True,
                        "message": f"Successfully uploaded {len(uploaded_file_ids)} files",
                        "file_ids": uploaded_file_ids,
                    }
                    if oversized_files:
                        response["oversized_files"] = oversized_files
                        response["warning"] = (
                            f"{len(oversized_files)} file(s) were not uploaded because they exceeded the 15 MB limit."
                        )
                    return context.res.json(response)
                else:
                    return context.res.json({"error": "No files uploaded under 'media' field"}, 400)
            else:
                return context.res.json(
                    {"error": "User is not valid or authentication failed", "auth_response": resp_json}, 401
                )

        else:
            return context.res.json({"error": "Content-Type must be multipart/form-data"}, 400)
    return context.res.json(
        {
            "data": "Only Post method is allowed",
            "method": context.req.method,
            "path": context.req.path,
            "headers": context.req.headers,
        }
    )
