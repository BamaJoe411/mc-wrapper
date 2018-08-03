'''
A modified version of Python Buycraft API by minecrafter
https://github.com/minecrafter/buycraft-python
'''

import re, requests, threading
from time import sleep


class BuycraftException(Exception):
    pass


class Buycraft(threading.Thread):

    def __init__(self, wrapper):
        super().__init__()
        self.wrapper = wrapper

        self.url = 'https://plugin.buycraft.net'
        self.get = {}

        self.send = self.wrapper.server.send
        self.player_list = self.wrapper.server.list


    def run(self):
        while self.enabled:

            self.get = self.get_due_players()

            if self.get["meta"]["execute_offline"]:
                offline = self.get_offline_commands()

                done = []

                for command in offline["commands"]:
                    command["player"]["username"] = command["player"]["name"]


                    for key in command["player"]: # Because it's very likely that there's json in the commands
                        command["command"] = command["command"].replace("{{{}}}".format(key), command["player"][key])

                    self.send(command["command"])

                    done.append(command["id"])


                if done:
                    self.mark_commands_completed(done)

            self.online_commands()

            n = 0
            while self.enabled and n < self.get["meta"]["next_check"]: # Keep checking if the wrapper is closed every second
                n += 1
                sleep(1)


    def online_commands(self):

        done = []

        for player in list(self.get["players"]):
            if player["name"] in self.player_list:
                commands = self.get_player_commands(player["id"])


                for command in commands["commands"]:
                    player["username"] = player["name"]

                    for key in player: # Because it's very likely that there's json in the commands and just using .format would mess up
                        command["command"] = command["command"].replace("{{{}}}".format(key), "{}".format(player[key]))

                    self.send(command["command"])
                    done.append(command["id"])

                self.get["players"].remove(player)


        if done:
            self.mark_commands_completed(done)


    def stop(self):
        self.enabled = False

    def setConfig(self, config):
        self.enabled = config["buycraft"]["enabled"]
        self.secret = config["buycraft"]["key"]





    def _getjson(self, url):
        response = requests.get(url, headers={'X-Buycraft-Secret': self.secret}).json()
        if 'error_code' in response:
            raise BuycraftException('Error code ' + str(response['error_code']) + ': ' + response['error_message'])
        return response

    def information(self):
        """Returns information about the server and the webstore.
        """
        return self._getjson(self.url + '/information')

    def listing(self):
        """Returns a listing of all packages available on the webstore.
        """
        return self._getjson(self.url + '/listing')

    def get_due_players(self, page=None):
        """Returns a listing of all players that have commands available to run.

        :param page: the page number to use
        """
        if page is None:
            return self._getjson(self.url + '/queue')
        elif isinstance(page, int):
            return self._getjson(self.url + '/queue?page=' + str(page))
        else:
            raise BuycraftException("page parameter is not valid")

    def get_offline_commands(self):
        """Returns a listing of all commands that can be run immediately.
        """
        return self._getjson(self.url + '/queue/offline-commands')

    def get_player_commands(self, player_id):
        """Returns a listing of all commands that require a player to be run.
        """
        if isinstance(player_id, int):
            return self._getjson(self.url + '/queue/online-commands/' + str(player_id))
        else:
            raise BuycraftException("player_id parameter is not valid")

    def mark_commands_completed(self, command_ids):
        """Marks the specified commands as complete.

        :param command_ids: the IDs of the commands to mark completed
        """
        resp = requests.delete(self.url + '/queue', params={'ids[]': command_ids},
                               headers={'X-Buycraft-Secret': self.secret})
        return resp.status_code == 204

    def recent_payments(self, limit):
        """Gets the rest of recent payments made for this webstore.

        :param limit: the maximum number of payments to return. The API will only return a maximum of 100.
        """
        if isinstance(limit, int):
            return self._getjson(self.url + '/payments')
        else:
            raise BuycraftException("limit parameter is not valid")

    def create_checkout_link(self, username, package_id):
        """Creates a checkout link for a package.

        :param username: the username to use for this package
        :param package_id: the package ID to check out
        """
        if not isinstance(username, str) or len(username) > 16 or not re.match('\w', username):
            raise BuycraftException("Username is not valid")

        if not isinstance(package_id, int):
            raise BuycraftException("Package ID is not valid")

        response = requests.post(self.url + '/checkout', params={'package_id': package_id, 'username': username},
                                 headers={'X-Buycraft-Secret': self.secret}).json()
        if 'error_code' in response:
            raise BuycraftException('Error code ' + str(response['error_code']) + ': ' + response['error_messages'])
        return response
