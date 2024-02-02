import os

class Config:

    def __init__(self) -> None:
        self.postgres_host = "localhost"
        self.postgres_port = "5432"
        self.postgres_user = "postgres"
        self.postgres_password = "postgres"
        self.ossapi_id = ""
        self.ossapi_secret = ""
        self.storage = "../storage"
        self.logs_storage = "../logs"
        self.load_env()
        os.makedirs(self.storage, exist_ok=True)

    def load_env(self):
        for k,v in os.environ.items():
            if k.lower() in self.__dict__:
                self.__dict__[k.lower()] = v

