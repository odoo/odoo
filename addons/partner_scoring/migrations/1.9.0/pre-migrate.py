import logging

_logger = logging.getLogger(__name__)

# auto_install marks a module only when one of its dependencies is being
# installed in the same run (modules/db.py, _AUTO_INSTALL_CANDIDATES_QUERY): on
# a database where partner_scoring and sale, crm or account_credit are already
# installed, nothing is "to install" and the bridge stays uninstalled through
# every -u. The convergence loop re-reads the states after each pass, so a
# bridge marked here is loaded in this run, the way the credit satellites were.
BRIDGES = (
    "partner_scoring_sale",
    "partner_scoring_crm",
    "account_credit_partner_scoring",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_module_module m
           SET state = 'to install'
         WHERE m.name = ANY(%s)
           AND m.state = 'uninstalled'
           AND NOT EXISTS (
                SELECT 1 FROM ir_module_module_dependency d
                LEFT JOIN ir_module_module dep ON dep.name = d.name
                 WHERE d.module_id = m.id
                   AND (dep.id IS NULL
                        OR dep.state NOT IN ('installed', 'to upgrade', 'to install'))
           )
        RETURNING m.name
        """,
        (list(BRIDGES),),
    )
    marked = [name for (name,) in cr.fetchall()]
    if marked:
        _logger.info(
            "partner_scoring 1.9.0: %s marked to install, every dependency present",
            ", ".join(marked),
        )
