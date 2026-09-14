#!/usr/bin/env python3
import os
import sys


def is_encryption_setup_valid():
    env_var = "ODOO_API_ENCRYPTION_KEY"
    key = os.environ.get(env_var)

    if not key:
        return False

    if len(key) != 44:
        return False

    try:
        from cryptography.fernet import Fernet

        cipher = Fernet(key.encode())
    except Exception:
        return False

    try:
        test_data = "sk_test_1234567890_this_is_a_secret_api_key"

        encrypted = cipher.encrypt(test_data.encode())

        decrypted = cipher.decrypt(encrypted).decode()

        if decrypted == test_data:
            pass
        else:
            return False

    except Exception:
        return False

    key[:8] + "..." + key[-8:]

    return True


def main():
    try:
        pass
    except ImportError:
        sys.exit(1)

    success = is_encryption_setup_valid()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
