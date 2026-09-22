import logging

_logger = logging.getLogger(__name__)

# The contract documents, the group that may read them and their cache left
# api_doc for rpc; the playground stays. Their external ids move with them,
# before either module loads its data.
MOVED = ("group_allow_doc",)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE ir_model_data SET module = 'rpc' "
        "WHERE module = 'api_doc' AND name = ANY(%s) "
        "AND NOT EXISTS (SELECT 1 FROM ir_model_data kept "
        "WHERE kept.module = 'rpc' AND kept.name = ir_model_data.name)",
        [list(MOVED)],
    )
    _logger.info("rpc 1.1: %s external id(s) moved from api_doc", cr.rowcount)
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'api_doc' AND name = ANY(%s)",
        [list(MOVED)],
    )
