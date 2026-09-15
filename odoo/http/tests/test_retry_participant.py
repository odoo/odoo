from unittest.mock import MagicMock

import pytest

from odoo.http._retry import RequestRetryParticipant


def _request(**kwargs):
    request = MagicMock(**kwargs)
    request._load_session.return_value = MagicMock()
    return request


class TestOnRollback:
    def test_the_session_snapshot_is_restored_not_reloaded_from_disk(self):
        request = _request()

        RequestRetryParticipant(request).on_rollback(Exception("boom"))

        request._restore_session_snapshot.assert_called_once_with()
        request._load_session.assert_not_called()


class TestOnRetry:
    def test_seekable_uploads_are_rewound(self):
        upload = MagicMock()
        upload.seekable.return_value = True
        request = _request()
        request.httprequest.files.items.return_value = [("photo", upload)]

        RequestRetryParticipant(request).on_retry(Exception("boom"))

        upload.seek.assert_called_once_with(0)

    def test_a_non_seekable_upload_raises_rather_than_replaying_a_partial_stream(self):
        upload = MagicMock()
        upload.seekable.return_value = False
        request = _request()
        request.httprequest.files.items.return_value = [("upload", upload)]

        with pytest.raises(
            RuntimeError, match="Cannot retry request on input file 'upload'"
        ):
            RequestRetryParticipant(request).on_retry(Exception("boom"))

    def test_the_replay_hook_is_invoked(self):
        request = _request()
        request.httprequest.files.items.return_value = []
        RequestRetryParticipant(request).on_retry(Exception("boom"))
        request._reset_for_replay.assert_called_once_with()

    def test_a_request_without_the_replay_hook_does_not_crash(self):
        request = MagicMock(spec=["_load_session", "httprequest", "session"])
        request.httprequest.files.items.return_value = []
        assert not hasattr(request, "_reset_for_replay")
        RequestRetryParticipant(request).on_retry(Exception("boom"))


class TestUncommittedWarningSuppression:
    def test_a_detached_database_suppresses_the_warning(self):
        request = _request(database_detached=True)
        assert RequestRetryParticipant(request).is_uncommitted_warning_suppressed()

    def test_an_ordinary_request_does_not(self):
        request = _request(database_detached=False)
        assert not RequestRetryParticipant(request).is_uncommitted_warning_suppressed()

    def test_a_stand_in_request_without_the_attribute_does_not(self):
        request = MagicMock(spec=["_load_session", "httprequest", "session"])
        assert not RequestRetryParticipant(request).is_uncommitted_warning_suppressed()


class TestNoAmbientParticipant:
    def test_importing_http_installs_nothing_on_the_transaction_primitive(self):
        import odoo.http  # noqa: F401  the import is the side effect under test
        import odoo.service.transaction as tx

        assert not hasattr(tx, "current_retry_participant")
