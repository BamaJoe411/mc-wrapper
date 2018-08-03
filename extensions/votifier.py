'''
An extension that allows for detecting votes on server lists and sending commands as rewards
'''

import threading, socket, re
from Crypto.PublicKey import RSA
from Crypto import Random

class Votifier(threading.Thread):

    def __init__(self, wrapper):
        super().__init__()
        self.wrapper = wrapper
        self.send = self.wrapper.server.send

        self.running = False


    def generateKeys():
        generator = Random.new().read

        private_key = RSA.generate(2048, generator)
        public_key = private_key.publickey()

        with open('config/private.pem', 'w') as f:
            f.write(private_key.exportKey(format='PEM').decode())

        with open('config/public.pem', 'w') as f:
            f.write(public_key.exportKey(format='PEM').decode())

    def getKey(self):
        public_key = self.private_key.publickey().exportKey(format='PEM').decode()

        return re.findall(r'^-----BEGIN PUBLIC KEY-----([\s\S]+)-----END PUBLIC KEY-----$', public_key)[0].replace("\n","")


    def run(self):

        while self.enabled and self.config_changed:

            self.config_changed = False

            serversocket = socket.socket()
            serversocket.bind((self.ip, self.port))

            serversocket.listen(5)

            self.running = True

            try:
                while self.running:
                    conn, addr = serversocket.accept()

                    code = self.private_key.decrypt(conn.recv(self.buffer))

                    try:
                        if b"VOTE" in code:

                            vote = {}

                            try:
                                vote["service_name"], vote["username"], vote["address"], vote["time_stamp"] = [i.decode() for i in code.split(b"VOTE")[1].split()[:4]]

                                if re.search(r'^[A-Za-z0-9_]+$', vote["username"]):

                                    out = ""
                                    for command in self.commands:
                                        for key in vote: # Because it's very likely that there's json in the commands
                                            command = command.replace("{{{}}}".format(key), vote[key])

                                        out += command + "\n"

                                    self.send(out)

                                    with open('logs/votifier.log', 'a') as f:
                                        f.write("{username} ({address}) has voted on {service_name}\n".format(**vote))


                            except AttributeError:
                                pass

                    finally:
                        conn.close()

            finally:
                serversocket.close()


    def stop(self):
        if self.running:
            self.running = False
            socket.socket().connect((self.ip, self.port)) # connect to socket, so it'll check self.running again


    def setConfig(self, config):
        self.config_changed = True

        self.enabled = config["votifier"]["enabled"]
        self.ip = config["votifier"]["ip"]
        self.port = config["votifier"]["port"]
        self.commands = config["votifier"]["commands"]
        self.private_key = RSA.importKey(config["votifier"]["private_key"])
        self.buffer = 256

        self.stop()