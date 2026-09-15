import pytest
from cryptography.fernet import Fernet

from odoo.libs import sealing


def _key():
    return Fernet.generate_key().decode()


def test_a_sealed_value_opens_to_its_plaintext():
    environ = {sealing.ENV_KEY: _key()}
    sealed = sealing.seal("the-secret", environ)

    assert sealing.is_sealed(sealed)
    assert "the-secret" not in sealed
    assert sealing.unseal(sealed, environ) == "the-secret"


def test_nothing_is_sealed_without_a_key():
    with pytest.raises(sealing.SealError):
        sealing.seal("the-secret", {})


def test_a_value_sealed_under_a_rotated_key_opens_with_its_numbered_predecessor():
    old, new = _key(), _key()
    sealed = sealing.seal("the-secret", {sealing.ENV_KEY: old})

    rotated = {sealing.ENV_KEY: new, f"{sealing.ENV_KEY}_V1": old}

    assert sealing.unseal(sealed, rotated) == "the-secret"


def test_a_wrong_key_or_no_key_refuses_to_open():
    sealed = sealing.seal("the-secret", {sealing.ENV_KEY: _key()})

    with pytest.raises(sealing.SealError):
        sealing.unseal(sealed, {sealing.ENV_KEY: _key()})
    with pytest.raises(sealing.SealError):
        sealing.unseal(sealed, {})


def test_an_unsealed_value_is_not_opened():
    with pytest.raises(sealing.SealError):
        sealing.unseal("plain", {sealing.ENV_KEY: _key()})


def test_old_key_versions_stop_after_two_missing_numbers():
    environ = {
        f"{sealing.ENV_KEY}_V1": "a",
        f"{sealing.ENV_KEY}_V2": "b",
        f"{sealing.ENV_KEY}_V5": "c",
    }

    assert sealing.old_key_versions(environ) == [1, 2]
