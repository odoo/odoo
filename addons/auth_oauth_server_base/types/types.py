from typing import Literal, TypedDict

AuthMethod = Literal['none', 'client_secret_basic', 'client_secret_post']
ClientType = Literal['public', 'confidential']


class ClientRegistrationResult(TypedDict):
    client_id: str
    client_secret: str


class TokenGrantResult(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str
