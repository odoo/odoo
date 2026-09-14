import logging

_logger = logging.getLogger(__name__)

_ENDPOINT_CODE = "openai"
_SEEDED_VALUE = "gpt-4o"
_CATALOG_VALUE = "gpt-4o-mini"


def migrate(cr, version):
    cr.execute(
        """
        UPDATE gateway_ml_provider p
           SET default_model = %s
          FROM integration_service e
         WHERE p.endpoint_id = e.id
           AND e.code = %s
           AND p.default_model = %s
        """,
        (_CATALOG_VALUE, _ENDPOINT_CODE, _SEEDED_VALUE),
    )
    if cr.rowcount:
        _logger.info(
            "19.0.1.5.0: %s openai provider row(s) moved from the seeded %r to "
            "the catalog's %r. Rows carrying any other value were left alone — "
            "that is an administrator's override, not the stale seed.",
            cr.rowcount,
            _SEEDED_VALUE,
            _CATALOG_VALUE,
        )
