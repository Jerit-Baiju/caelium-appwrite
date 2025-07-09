import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = os.environ["SMTP_EMAIL"]
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(os.environ["SMTP_EMAIL"], os.environ["SMTP_PASSWORD"])
    server.sendmail(msg["From"], msg["To"], msg.as_string())
    server.quit()


def main(context):
    try:
        data = json.loads(context.req.body)

        messages = []

        # Bulk with same body
        if isinstance(data.get("to"), list):
            for email in data["to"]:
                messages.append({"to": email, "subject": data.get("subject", ""), "body": data.get("body", "")})

        # Bulk with different content
        elif "messages" in data:
            messages = data["messages"]

        # Single email
        elif "to" in data and "subject" in data and "body" in data:
            messages.append({"to": data["to"], "subject": data["subject"], "body": data["body"]})
        else:
            return context.res.json({"error": "Invalid input"}, 400)

        success = 0
        failed = 0
        failed_list = []

        for msg in messages:
            try:
                send_email(msg["to"], msg["subject"], msg["body"])
                success += 1
            except Exception as e:
                failed += 1
                failed_list.append({"to": msg["to"], "error": str(e)})

        return context.res.json({"sent": success, "failed": failed, "errors": failed_list}, 200)

    except Exception as e:
        return context.res.json({"error": str(e)}, 500)
