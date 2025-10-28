import os

import requests


def main(context):

    if context.req.method != "POST":
        return context.res.json({"error": "Method Not Allowed"})

    servers = requests.get("https://cs1.caelium.co/api/core/servers").json()
    for server in servers:
        if not server["active_status"]:
            resp = requests.get(
                f"{server['base_url']}/api/core/ping/", json={"secret": os.environ["SECRET_KEY"]}, timeout=5
            )
            if resp.status_code == 200:
                if not server["release_update_status"]:
                    resp = requests.post(
                        f"{server['base_url']}/api/core/update/",
                        json={"secret": os.environ["SECRET_KEY"], "server_id": server["id"]},
                    )
                resp = requests.post(
                    "https://cs1.caelium.co/api/core/update_server_status/",
                    json={"secret": os.environ["SECRET_KEY"], "server_id": server["id"], "status": True},
                )

            print(resp.json())
    return context.res.json(servers)
