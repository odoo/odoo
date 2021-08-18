import json
import requests


class ProfileAPI:
    MARKETPLACE_HOST = "https://dev-mpapi.aumet.tech"
    HEADERS = {
        'Content-Type': 'application/json',
        'x-user-lang': 'en',
        'x-api-key': 'zTvkXwJSSRa5DVvTgQhaUW52DkpkeSz',
        'x-session-id': '123',
        'Cookie': 'PHPSESSID=adl0oj5l20ufa78t4ij2s7nl91'
    }

    @classmethod
    def login(cls, email, password):
        payload = json.dumps({
            "email": email,
            "password": password
        })

        response = requests.post(f"{cls.MARKETPLACE_HOST}/v1/users/signin-password", headers=cls.HEADERS, data=payload)

        return response.json()

    @classmethod
    def get_profile_info(cls, token):
        headers = cls.HEADERS
        headers.update({"x-access-token": token})
        response = requests.get(f"{cls.MARKETPLACE_HOST}/v1/users/profile", headers=cls.HEADERS)
        return response.json()
