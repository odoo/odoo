import logging

_logger = logging.getLogger(__name__)

_SEEDED_CODES = (
    "claude",
    "deepseek",
    "openai",
    "gemini",
    "gemini_openai",
    "deepgram",
    "groq",
    "moonshot",
)


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE integration_service
           SET endpoint_url_test = NULL
         WHERE code = ANY(%s)
           AND endpoint_url_test IS NOT NULL
           AND endpoint_url_test = endpoint_url
        """,
        [list(_SEEDED_CODES)],
    )
    if cr.rowcount:
        _logger.info(
            "gateway_ml 19.0.1.8.0: cleared endpoint_url_test on %s AI endpoint(s) "
            "that pointed 'test' at the vendor's production API; outbound calls "
            "now fall back to endpoint_url, which is where they already went",
            cr.rowcount,
        )
