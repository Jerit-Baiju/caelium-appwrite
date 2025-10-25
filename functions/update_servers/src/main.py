import os

import requests


def main(context):

    if context.req.method != "POST":
        return context.res.json({"error": "Method Not Allowed"})

    servers = requests.get("https://cs1.caelium.co/api/core/servers").json()
    for server in servers:
        
        if server["active_status"]:
            resp = requests.post(f"{server['base_url']}/api/core/update_release/", json={"secret": os.environ["SECRET_KEY"]})
            print(resp.status_code)
            if resp.status_code != 200:
                resp = requests.post(
                    f"{server['base_url']}/api/core/update_server_status/",
                    json={"secret": os.environ["SECRET_KEY"], "server_id": server["id"]},
                )
            print(resp.json())
        else:
            resp = requests.post(
                "https://cs1.caelium.co/api/core/release_update_failure/",
                json={"secret": os.environ["SECRET_KEY"], "server_id": server["id"]},
            )
            
            print(resp.json())

    print(servers)

    return context.res.json(servers)
