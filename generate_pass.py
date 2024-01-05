import bcrypt
from passlib.context import CryptContext

setpw = CryptContext(schemes=['pbkdf2_sha512'])
hashed_password = setpw.encrypt('dua1molle')
# The `hashed_password` can be stored in the database

print(hashed_password)