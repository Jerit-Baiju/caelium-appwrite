import json


def main(context):
    if context.req.path == "/ping":
        return context.res.text("Pong")

    if context.req.method == "POST":
        try:
            body_str = context.req.body_binary.decode("utf-8")
            data = json.loads(body_str)
            context.log(data)
            return context.res.json({"received": data})
        except UnicodeDecodeError:
            return context.res.json({"error": "Request body is not valid UTF-8 text."})
        except json.JSONDecodeError:
            return context.res.json({"error": "Request body is not valid JSON."})

    return context.res.json(
        {
            "motto": "this was just a test message",
            "learn": "https://appwrite.io/docs",
            "connect": "https://appwrite.io/discord",
            "getInspired": "https://builtwith.appwrite.io",
        }
    )
