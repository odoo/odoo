import re

import pytest

from odoo.libs import redact


@pytest.fixture
def registered():
    before = list(redact.REGISTERED_PATTERNS)
    yield
    redact.REGISTERED_PATTERNS[:] = before


class TestKeys:
    @pytest.mark.parametrize(
        "key",
        ["password", "X-Api-Key", "client_secret", "Authorization", "x-amz-signature"],
    )
    def test_a_secret_named_key_is_sensitive(self, key):
        assert redact.is_sensitive_key(key)

    def test_an_ordinary_key_is_not(self):
        assert not redact.is_sensitive_key("partner_name")


class TestText:
    def test_the_value_after_a_label_is_masked_with_either_separator(self):
        masked = redact.mask_text("token=abc123 password: hunter2")
        assert "abc123" not in masked
        assert "hunter2" not in masked
        assert masked.count(redact.MASK) == 2

    @pytest.mark.parametrize(
        "secret",
        [
            "ghp_" + "a" * 36,
            "sk-" + "b" * 48,
            "AKIA" + "C" * 16,
        ],
    )
    def test_a_secret_of_a_known_shape_is_masked_without_a_label(self, secret):
        assert secret not in redact.mask_text(f"vendor rejected {secret} today")

    def test_a_private_key_block_is_masked_whole(self):
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nAAAA\n-----END RSA PRIVATE KEY-----"
        masked = redact.mask_text(f"bad key:\n{pem}\nretry")
        assert "MIIEow" not in masked
        assert masked.endswith("retry")

    def test_a_url_inside_text_loses_its_userinfo_and_secret_query(self):
        masked = redact.mask_text(
            "GET https://u:p@api.invalid/x?api_key=k1&page=2 failed"
        )
        assert "u:p@" not in masked
        assert "k1" not in masked
        assert "page=2" in masked

    def test_plain_text_is_left_alone(self):
        assert redact.mask_text("nothing secret here") == "nothing secret here"


class TestRegisteredPatterns:
    def test_a_registered_shape_is_masked_in_text_and_urls(self, registered):
        redact.register_pattern(r"bot(\d+):[A-Za-z0-9_-]+", r"bot\1:***")
        assert "SECRET" not in redact.mask_text("call bot42:SECRET failed")
        assert "SECRET" not in redact.mask_url("https://t.invalid/bot42:SECRET/getMe")

    def test_a_compiled_pattern_and_a_callable_replacement_are_accepted(
        self, registered
    ):
        redact.register_pattern(re.compile(r"key-\w+"), lambda match: "key-***")
        assert redact.mask_text("key-abc") == "key-***"


class TestData:
    def test_nested_secret_keys_are_masked_and_the_rest_kept(self):
        data = {"user": "ann", "auth": {"token": "t"}, "items": [{"password": "p"}]}
        assert redact.mask_data(data) == {
            "user": "ann",
            "auth": redact.MASK,
            "items": [{"password": redact.MASK}],
        }

    def test_nesting_past_the_limit_is_dropped(self):
        data = {"a": {"b": {"c": {"d": 1}}}}
        assert redact.mask_data(data, max_depth=1) == {
            "a": {"b": "***REDACTED_DEEP_NESTING***"}
        }


class TestFindSecretShapes:
    def test_the_names_of_every_matching_shape_are_reported(self):
        found = redact.find_secret_shapes("password=x and AKIA" + "D" * 16)
        assert found == ["password", "aws_access_key_id"]

    def test_nothing_is_reported_for_ordinary_notes(self):
        assert redact.find_secret_shapes("rotate every quarter") == []
