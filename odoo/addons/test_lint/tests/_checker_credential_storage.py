import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass

# The vault holds its own values; it cannot reference itself.
VAULT_MODULE = "credential"

SECRET = re.compile(
    r"(password|secret|api_?key|token|passphrase|private_key|client_secret"
    r"|credential|_key$)",
    re.IGNORECASE,
)
# Handed to browsers on purpose; vaulting one protects nothing.
PUBLIC_KEY = re.compile(
    r"(public_key|publishable_key|site_key|website_key|client_key)$", re.IGNORECASE
)
# An index, a lookup, a keyboard key: not a credential in any sense.
NOT_A_KEY = re.compile(
    r"^(cache_key|bucket_key|grouping_key|job_key|period_key|source_key"
    r"|partner_key|zip_key|website_form_key|avatar_cache_key|push_to_talk_key"
    r"|attendance_kiosk_key|identity_key|booking_key)$",
    re.IGNORECASE,
)
# Names that are about a secret rather than one.
ABOUT = re.compile(
    r"(token_type|_expir|has_|is_|use_|show_|_count|_url|_uri|_header|_name"
    r"|_id$|_ids$|_state|_status|_method|_type$|_scheme$|_endpoint$)",
    re.IGNORECASE,
)
# A capability we mint so a link works; moving it into the vault breaks the URL.
SHARE = re.compile(
    r"^(share_token|invite_token|document_token|portal_token|signup_token)$"
)
# Computed from a secret, and the point of them is that they are not it.
DERIVED = re.compile(r"(_hash|_masked|_fingerprint|_encrypted|_plain|_display)$")
# A cursor the counterparty hands back so the next call resumes a feed.
CURSOR = re.compile(r"(sync_token|page_token|next_token|_cursor)$", re.IGNORECASE)

# Decided per field, because the name does not say: identifiers printed on a
# document or sent in the clear, and tokens that authorise a visitor to one of
# our records rather than us to somebody's API, or that we publish on purpose.
JUDGED_NOT_SECRET = frozenset(
    {
        "appointment_google_reserve.google_reserve_idempotency_token",
        "approval.subject_key",
        "auth_passkey.credential_identifier",
        "delivery_fedex.fedex_developer_key",
        "delivery_fedex_rest.fedex_rest_developer_key",
        "sale_lazada.app_key",
        "l10n_br_edi.l10n_br_access_key",
        "l10n_br_edi_pos.l10n_br_access_key",
        "sale_amazon.seller_key",
        "website.google_analytics_key",
        "website_slides.website_slide_google_app_key",
        "base.access_token",
        "calendar.access_token",
        "calendar.booking_access_token",
        "document.access_token",
        "frontdesk.access_token",
        "hr_contract_salary.access_token",
        "iot.token",
        "mail.access_token",
        "planning.access_token",
        "point_of_sale.access_token",
        "portal.access_token",
        "pos_enterprise.access_token",
        "rating.access_token",
        "room.access_token",
        "sign.access_token",
        "sign.sms_token",
        "sign.token",
        "social_push_notifications.push_token",
        "spreadsheet_dashboard.access_token",
        "survey.access_token",
        "website.access_token",
        "website_sale.access_token",
        "website_slides.access_token",
        "website.google_maps_api_key",
    }
)


@dataclass
class Violation:
    lineno: int
    col_offset: int
    message: str


def module_of(path: str) -> str:
    _head, sep, tail = path.rpartition("/addons/")
    return tail.split("/", 1)[0] if sep else ""


def _hashed_names(tree: ast.Module) -> set[str]:
    hashed: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "hash"
            for sub in ast.walk(node.value)
        ):
            continue
        for target in node.targets:
            name = getattr(target, "attr", None) or getattr(target, "id", None)
            if name:
                hashed.add(name)
    return hashed


def _is_transient(node: ast.ClassDef) -> bool:
    return bool(node.bases) and "TransientModel" in ast.unparse(node.bases[0])


def _keywords(call: ast.Call) -> dict[str, ast.expr]:
    return {keyword.arg: keyword.value for keyword in call.keywords if keyword.arg}


def _is_stored(keywords: dict[str, ast.expr]) -> bool:
    store = keywords.get("store")
    if isinstance(store, ast.Constant) and store.value is False:
        return False
    if isinstance(store, ast.Constant) and store.value is True:
        return True
    return not ("compute" in keywords or "related" in keywords)


def _looks_secret(module: str, name: str, hashed: set[str]) -> bool:
    return bool(
        SECRET.search(name)
        and not ABOUT.search(name)
        and not SHARE.match(name)
        and not DERIVED.search(name)
        and not CURSOR.search(name)
        and not PUBLIC_KEY.search(name)
        and not NOT_A_KEY.match(name)
        and name not in hashed
        and f"{module}.{name}" not in JUDGED_NOT_SECRET
    )


def check(tree: ast.Module, path: str) -> Iterator[Violation]:
    module = module_of(path)
    if not module or module == VAULT_MODULE:
        return
    hashed = _hashed_names(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        transient = _is_transient(node)
        for statement in node.body:
            if not (
                isinstance(statement, ast.Assign)
                and isinstance(statement.value, ast.Call)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
            ):
                continue
            call = statement.value
            if getattr(getattr(call.func, "value", None), "id", "") != "fields":
                continue
            if getattr(call.func, "attr", "") not in ("Char", "Text"):
                continue
            name = statement.targets[0].id
            if not _looks_secret(module, name, hashed):
                continue
            keywords = _keywords(call)
            if transient:
                if "config_parameter" in keywords:
                    yield Violation(
                        statement.lineno,
                        statement.col_offset,
                        f"{module}.{name} keeps a secret in ir.config_parameter, "
                        "in clear",
                    )
            elif _is_stored(keywords):
                yield Violation(
                    statement.lineno,
                    statement.col_offset,
                    f"{module}.{name} stores a secret in a plain column",
                )
