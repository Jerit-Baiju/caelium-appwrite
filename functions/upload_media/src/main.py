def main(context):
    if context.req.path == "/ping":
        return context.res.text("Pong")

    return context.res.json(
        {
            "motto": "this was just a test message",
            "learn": "https://appwrite.io/docs",
            "connect": "https://appwrite.io/discord",
            "getInspired": "https://builtwith.appwrite.io",
        }
    )
