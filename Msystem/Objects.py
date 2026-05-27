import utils.argon_utils as argon

class User:
    def __init__(self, login_user_name: str, hashed_pass: str) -> None:
        self.user_id:int = -1
        self.login_user_name = login_user_name
        self.hashed_pass = hashed_pass
    def verify_password(self, raw_password:str) -> bool:
        return argon.verify_password(self.hashed_pass, raw_password)


