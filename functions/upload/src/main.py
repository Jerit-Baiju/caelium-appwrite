import os

import requests


def main(context):
    if context.req.path == "/ping":
        return context.res.text("Pong")

    if os.environ.get("env") == "dev":
        data = open("/usr/local/server/src/function/src/data.json", "r", encoding="utf-8")
        response = data.read()
        data.close()
    else:
        response = requests.get(f'{os.environ["host"]}/api/cloud/unprocessed/').text

    return context.res.text(response)
