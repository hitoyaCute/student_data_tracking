from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16
)

# hash password
def hash_password(plain_password: str) -> str:
    return ph.hash(plain_password)

# very a password
def verify_password(hashed_pass: str, plain_password: str) -> bool:
    try:
        return ph.verify(hashed_pass, plain_password)
    except VerifyMismatchError:
        return False

def check_and_update_hash(hashed_pass: str, plain_password: str) -> str:
    if ph.check_needs_rehash(hashed_pass):
        return ph.hash(plain_password)
    return ""

