import requests
import json
import concurrent.futures

from lib.user import User
from lib.scenarioprinter import ScenarioPrinter
from lib import settings


class Admin:

    def __init__(self, sync_gateway):
        self.admin_url = "http://{}:4985".format(sync_gateway.ip)
        self.users = {}

        self._printer = ScenarioPrinter()

    def register_user(self, target, db, name, password, channels):

        headers = {"Content-Type": "application/json"}
        data = {"name": name, "password": password, "admin_channels": channels}

        r = requests.put("{0}/{1}/_user/{2}".format(self.admin_url, db, name), headers=headers, timeout=settings.HTTP_REQ_TIMEOUT, data=json.dumps(data))
        r.raise_for_status()

        self._printer.print_user_add()

        return User(target, db, name, password, channels)

    def register_bulk_users(self, target, db, name_prefix, number, password, channels):

        if type(channels) is not list:
            raise("Channels needs to be a list")

        users = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.MAX_REQUEST_WORKERS) as executor:
            futures = [executor.submit(self.register_user, target=target, db=db, name="{}_{}".format(name_prefix, i), password=password, channels=channels) for i in range(number)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    user = future.result()
                    users.append(user)
                except Exception as e:
                    raise("register_bulk_users failed: {}".format(e))

        if len(users) != number:
            raise("Not all users added during register_bulk users")

        return users
