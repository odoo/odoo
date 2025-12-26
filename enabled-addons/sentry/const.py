# Copyright 2016-2017 Versada <https://versada.eu/>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import collections
import logging

from sentry_sdk import HttpTransport
from sentry_sdk.consts import DEFAULT_OPTIONS
from sentry_sdk.integrations.logging import LoggingIntegration

import odoo.loglevels


def split_multiple(string, delimiter=",", strip_chars=None):
    """Splits :param:`string` and strips :param:`strip_chars` from values."""
    if not string:
        return []
    return [v.strip(strip_chars) for v in string.split(delimiter)]


def to_int_if_defined(value):
    if value == "" or value is None:
        return
    return int(value)


def to_float_if_defined(value):
    if value == "" or value is None:
        return
    return float(value)


SentryOption = collections.namedtuple("SentryOption", ["key", "default", "converter"])

# Mapping of Odoo logging level -> Python stdlib logging library log level.
LOG_LEVEL_MAP = {
    getattr(odoo.loglevels, f"LOG_{x}"): getattr(logging, x)
    for x in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET")
}
DEFAULT_LOG_LEVEL = "warn"

ODOO_USER_EXCEPTIONS = [
    "odoo.exceptions.AccessDenied",
    "odoo.exceptions.AccessError",
    "odoo.exceptions.DeferredException",
    "odoo.exceptions.MissingError",
    "odoo.exceptions.RedirectWarning",
    "odoo.exceptions.UserError",
    "odoo.exceptions.ValidationError",
    "odoo.exceptions.Warning",
    "odoo.exceptions.except_orm",
]
DEFAULT_IGNORED_EXCEPTIONS = ",".join(ODOO_USER_EXCEPTIONS)

EXCLUDE_LOGGERS = ("werkzeug",)
DEFAULT_EXCLUDE_LOGGERS = ",".join(EXCLUDE_LOGGERS)

DEFAULT_ENVIRONMENT = "develop"

DEFAULT_TRANSPORT = "threaded"


def select_transport(name=DEFAULT_TRANSPORT):
    return {
        "threaded": HttpTransport,
    }.get(name, HttpTransport)


def get_sentry_logging(level=DEFAULT_LOG_LEVEL):
    if level not in LOG_LEVEL_MAP:
        level = DEFAULT_LOG_LEVEL

    return LoggingIntegration(
        # Gather warnings into breadcrumbs regardless of actual logging level
        level=logging.WARNING,
        event_level=LOG_LEVEL_MAP[level],
    )


def get_sentry_options():
    res = [
        SentryOption("dsn", "", str.strip),
        SentryOption("transport", DEFAULT_OPTIONS["transport"], select_transport),
        SentryOption("logging_level", DEFAULT_LOG_LEVEL, get_sentry_logging),
        SentryOption(
            "include_local_variables", DEFAULT_OPTIONS["include_local_variables"], None
        ),
        SentryOption(
            "max_breadcrumbs", DEFAULT_OPTIONS["max_breadcrumbs"], to_int_if_defined
        ),
        SentryOption("release", DEFAULT_OPTIONS["release"], None),
        SentryOption("environment", DEFAULT_OPTIONS["environment"], None),
        SentryOption("server_name", DEFAULT_OPTIONS["server_name"], None),
        SentryOption("shutdown_timeout", DEFAULT_OPTIONS["shutdown_timeout"], None),
        SentryOption("integrations", DEFAULT_OPTIONS["integrations"], None),
        SentryOption(
            "in_app_include", DEFAULT_OPTIONS["in_app_include"], split_multiple
        ),
        SentryOption(
            "in_app_exclude", DEFAULT_OPTIONS["in_app_exclude"], split_multiple
        ),
        SentryOption(
            "default_integrations", DEFAULT_OPTIONS["default_integrations"], None
        ),
        SentryOption("dist", DEFAULT_OPTIONS["dist"], None),
        SentryOption(
            "sample_rate", DEFAULT_OPTIONS["sample_rate"], to_float_if_defined
        ),
        SentryOption("send_default_pii", DEFAULT_OPTIONS["send_default_pii"], None),
        SentryOption("http_proxy", DEFAULT_OPTIONS["http_proxy"], None),
        SentryOption("https_proxy", DEFAULT_OPTIONS["https_proxy"], None),
        SentryOption("ignore_exceptions", DEFAULT_IGNORED_EXCEPTIONS, split_multiple),
        SentryOption(
            "max_request_body_size", DEFAULT_OPTIONS["max_request_body_size"], None
        ),
        SentryOption("attach_stacktrace", DEFAULT_OPTIONS["attach_stacktrace"], None),
        SentryOption("ca_certs", DEFAULT_OPTIONS["ca_certs"], None),
        SentryOption("propagate_traces", DEFAULT_OPTIONS["propagate_traces"], None),
        SentryOption(
            "traces_sample_rate",
            DEFAULT_OPTIONS["traces_sample_rate"],
            to_float_if_defined,
        ),
    ]

    if "auto_enabling_integrations" in DEFAULT_OPTIONS:
        res.append(
            SentryOption(
                "auto_enabling_integrations",
                DEFAULT_OPTIONS["auto_enabling_integrations"],
                None,
            )
        )

    return res
