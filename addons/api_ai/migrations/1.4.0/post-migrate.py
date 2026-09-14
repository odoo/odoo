import logging

_logger = logging.getLogger(__name__)

_VENDOR_HEADERS = {
    "claude": ("x-api-key", "anthropic-version"),
    "gemini": ("x-goog-api-key", None),
}


def migrate(cr, version):
    for code, (key_header, version_header) in _VENDOR_HEADERS.items():
        cr.execute(
            """
            UPDATE integration_service
               SET api_key_header = %s,
                   api_version_header = %s
             WHERE code = %s
               AND (
                     api_key_header IS DISTINCT FROM %s
                  OR api_version_header IS DISTINCT FROM %s
                   )
            """,
            (key_header, version_header, code, key_header, version_header),
        )
        if cr.rowcount:
            _logger.info(
                "19.0.1.4.0: %s '%s' endpoint(s) now name their own key header "
                "(%s) instead of relying on a service-code branch in the "
                "shared credential layer.",
                cr.rowcount,
                code,
                key_header,
            )
