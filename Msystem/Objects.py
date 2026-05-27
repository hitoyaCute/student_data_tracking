import utils.argon_utils as argon

class User:
    def __init__(self, login_user_name: str, hashed_pass: str) -> None:
        self.user_id:        int  = -1
        self.user_name:      str  = ""
        self.login_user_name: str = login_user_name
        self.hashed_pass:    str  = hashed_pass
        self.user_type:      int  = -1   # 0 = student, 1 = teacher

        # populated after login depending on role
        self.data: list | None = None

    def verify_password(self, raw_password: str) -> bool:
        return argon.verify_password(self.hashed_pass, raw_password)

    def is_student(self) -> bool:
        return self.user_type == 0

    def is_teacher(self) -> bool:
        return self.user_type == 1
