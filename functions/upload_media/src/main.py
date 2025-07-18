import base64
import email
import os
from email import policy

import requests
from appwrite.client import Client, InputFile
from appwrite.services.storage import Storage


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
            form_data, files = parse_multipart_data(context.req.body_binary, content_type)

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
                return context.res.json({"error": "Invalid response from auth server"}, 500)

            if resp_json.get("valid") is True:
                # Get the uploaded files under the 'media' field
                uploaded_files = files.get("media", [])

                if uploaded_files:
                    storage = Storage(client)
                    uploaded_file_ids = []

                    # Process each uploaded file
                    for _, uploaded_file in enumerate(uploaded_files):
                        filename = uploaded_file["filename"]
                        file_content = uploaded_file["content"]

                        # Upload each file to storage
                        f = storage.create_file(
                            os.environ["BUCKET_ID"],
                            file=InputFile.from_bytes(file_content, filename=filename),
                            file_id="unique()",
                        )
                        uploaded_file_ids.append(f["$id"])

                    # Return the list of uploaded file IDs
                    return context.res.json(
                        {
                            "success": True,
                            "message": f"Successfully uploaded {len(uploaded_files)} files",
                            "file_ids": uploaded_file_ids,
                            "auth_token": auth_token,
                        }
                    )
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
