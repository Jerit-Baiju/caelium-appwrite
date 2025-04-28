def main(context):
    if context.req.path == "/ping":
        return context.res.text("Pong")

    return context.res.text("Hello World from Python!")
