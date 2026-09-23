import re
import time

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


class TestLeaksClosed:
    @pytest.mark.parametrize("scheme", ["Bearer", "Basic", "Digest"])
    def test_the_credential_after_an_authorization_scheme_is_masked(self, scheme):
        masked = redact.mask_text(f"Authorization: {scheme} eyJhbGciOi.payload.sig")
        assert "eyJhbGciOi" not in masked
        assert masked == f"Authorization: {scheme} {redact.MASK}"

    def test_a_bearer_token_without_a_label_is_masked(self):
        masked = redact.mask_text("vendor echoed Bearer abcdefghijkl123 back")
        assert "abcdefghijkl123" not in masked
        assert "Bearer" in masked

    def test_a_quoted_json_key_does_not_shield_its_value(self):
        masked = redact.mask_text(
            '{"password": "hunter 2", "api_key": "k", "u": "ann"}'
        )
        assert "hunter" not in masked
        assert '"k"' not in masked
        assert '"u": "ann"' in masked

    def test_a_quoted_value_cut_off_by_truncation_is_masked(self):
        assert "hunter" not in redact.mask_text('{"password": "hunter2')

    def test_a_suffixed_secret_key_is_masked(self):
        masked = redact.mask_text("aws_secret_access_key=AbC123 secret_key=x9")
        assert "AbC123" not in masked
        assert "x9" not in masked

    def test_a_url_fragment_loses_its_secret_pairs(self):
        masked = redact.mask_url("https://x.invalid/cb#access_token=abc123&state=s")
        assert "abc123" not in masked
        assert "state=s" in masked

    def test_a_masked_url_keeps_its_own_encoding(self):
        assert redact.mask_url("https://h.invalid/p?q=a%20b&token=x") == (
            f"https://h.invalid/p?q=a%20b&token={redact.MASK}"
        )

    @pytest.mark.parametrize(
        "pem",
        [
            "-----BEGIN PRIVATE KEY-----\nMIIE\n-----END PRIVATE KEY-----",
            "-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIE\n-----END ENCRYPTED PRIVATE KEY-----",
        ],
    )
    def test_a_pkcs8_private_key_is_found_and_masked(self, pem):
        assert redact.find_secret_shapes(pem) == ["private_key_pem"]
        assert "MIIE" not in redact.mask_text(pem)

    @pytest.mark.parametrize(
        "secret",
        [
            "sk-proj-" + "a" * 40,
            "sk-ant-api03-" + "b" * 80,
            "sk_live_" + "c" * 24,
        ],
    )
    def test_a_prefixed_vendor_key_is_found_and_masked(self, secret):
        assert secret not in redact.mask_text(f"key {secret} rejected")
        assert redact.find_secret_shapes(secret)


class TestKeyBoundaries:
    @pytest.mark.parametrize("key", ["author", "author_id", "oauth_provider_name"])
    def test_a_word_that_merely_contains_auth_is_not_sensitive(self, key):
        assert not redact.is_sensitive_key(key)

    @pytest.mark.parametrize(
        "key", ["auth", "x-auth", "authToken", "AuthHeader", "accessToken", "apiKey"]
    )
    def test_auth_as_a_word_and_camel_case_secrets_are_sensitive(self, key):
        assert redact.is_sensitive_key(key)

    def test_an_author_label_in_text_keeps_its_value(self):
        assert redact.mask_text("author: Bob") == "author: Bob"

    def test_a_token_count_is_not_a_token(self):
        assert redact.mask_text("prompt_tokens: 120") == "prompt_tokens: 120"


class TestDataLeaves:
    def test_a_string_leaf_is_masked_as_text(self):
        data = {"message": "password=hunter2", "url": "https://h.invalid/?token=abc"}
        masked = redact.mask_data(data)
        assert "hunter2" not in masked["message"]
        assert "abc" not in masked["url"]

    def test_a_name_value_pair_is_masked_by_its_name(self):
        data = [{"name": "api_key", "value": "sk-live-xyz"}, {"name": "q", "value": 1}]
        assert redact.mask_data(data) == [
            {"name": "api_key", "value": redact.MASK},
            {"name": "q", "value": 1},
        ]

    def test_header_tuples_are_walked(self):
        data = [("Authorization", "Bearer abc"), ("Accept", "text/plain")]
        assert redact.mask_data(data) == [
            ("Authorization", redact.MASK),
            ("Accept", "text/plain"),
        ]

    def test_a_set_of_strings_is_walked(self):
        assert redact.mask_data({"token=abc"}) == {f"token={redact.MASK}"}


def test_a_key_followed_by_a_run_of_separators_is_linear():
    start = time.perf_counter()
    redact.mask_text("password" + "_" * 5000 + "!")
    redact.mask_text("secret" + "-_" * 5000 + "!")
    assert time.perf_counter() - start < 1.0
