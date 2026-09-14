from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from odoo.models import BaseModel
from odoo.tools import consteq


def get_url_with_params(
    url_string, query_params, remove_duplicates=True, *, doseq=False
):
    """Merge query parameters while preserving the URL path and fragment.

    Replace only supplied keys by default; repeated unrelated keys and blank
    values retain their meaning. Set ``remove_duplicates=False`` to append,
    or ``doseq=True`` to encode sequence values as repeated parameters.
    """
    if not query_params:
        return url_string
    url = urlsplit(url_string)
    url_params = parse_qsl(url.query, keep_blank_values=True)
    if remove_duplicates:
        url_params = [
            (key, value) for key, value in url_params if key not in query_params
        ]
    url_params.extend(query_params.items())
    return urlunsplit(url._replace(query=urlencode(url_params, doseq=doseq)))


def resolve_message_thread(message: BaseModel) -> BaseModel:
    if not message.res_id or not message._is_thread_model():
        return message.env["mixin.mail.thread"]
    return message._get_thread_model().browse(message.res_id)


def resolve_thread_for_credentials(thread: BaseModel) -> BaseModel:
    return thread.exists() if thread.ids else thread


def is_thread_hash_pid_valid(
    thread: BaseModel,
    _hash: str | None,
    pid: int | str | None,
) -> bool:
    if not isinstance(_hash, str) or not _hash or not pid:
        return False
    if thread._mail_post_token_field not in thread._fields:
        return False
    if isinstance(pid, bool) or not isinstance(pid, (int, str)):
        return False
    try:
        pid = int(pid)
    except ValueError:
        return False
    if consteq(_hash, thread._sign_token(pid)):
        return True
    parent_sign_token = thread._portal_get_parent_hash_token(pid)
    return bool(parent_sign_token) and consteq(_hash, parent_sign_token)


def is_thread_token_valid(thread: BaseModel, token: str | None) -> bool:
    token_field = thread._mail_post_token_field
    if not isinstance(token, str) or not token or token_field not in thread._fields:
        return False
    stored_token = thread[token_field]
    return bool(stored_token) and consteq(token, stored_token)


def get_portal_partner(
    thread: BaseModel,
    _hash: str | None,
    pid: int | str | None,
    token: str | None,
) -> BaseModel:
    thread = resolve_thread_for_credentials(thread)
    if not thread:
        return thread.env["res.partner"]
    if is_thread_hash_pid_valid(thread, _hash, pid):
        return thread.env["res.partner"].sudo().browse(int(pid)).exists()
    if is_thread_token_valid(thread, token):
        if partner := thread._mail_get_partners()[thread.id][:1]:
            return partner
    return thread.env["res.partner"]
