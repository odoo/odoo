"""Pre-migration: ``ir.mail_server`` moved from ``base`` into ``mail``.

The records stay -- the table, the views, the action, the menu, the access
rule -- only their owner changes. Every ``ir_model_data`` row ``base`` wrote for
the model is re-homed to ``mail`` so that ``mail``'s data load finds and updates
the same records instead of creating new ones, and so that ``_process_end``
does not reap ``base``'s rows as orphans and the records behind them with it.

A row is left alone when ``mail`` already owns one of the same name: the
reflection of a shared model gives every module its own ``model_ir_mail_server``
and ``field_ir_mail_server__id``, so ``base``'s copy is then just a duplicate
and ``_process_end`` drops the stale xml id while keeping the record.

``mail.ir_mail_server_view_form``, the inherited view that added the owner
fields, is folded into the form itself; its record is deleted here rather than
left to ``_process_end`` so that it never inherits from a form whose xml id no
longer resolves mid-load.

The three data repairs that ``base`` 1.9 ran on the table ride along, because
``base`` no longer owns a migration for a table it does not declare; each only
touches rows that are still wrong, so a database that already ran them changes
nothing.
"""

import logging

_logger = logging.getLogger(__name__)

XMLID_PATTERNS = (
    "model_ir_mail_server",
    "field_ir_mail_server__%",
    "selection__ir_mail_server__%",
    "constraint_ir_mail_server_%",
    "access_ir_mail_server",
    "ir_mail_server_form",
    "ir_mail_server_list",
    "view_ir_mail_server_search",
    "action_ir_mail_server_list",
    "menu_mail_servers",
)


def migrate(cr, version):
    if not version:
        return
    _rehome_xmlids(cr)
    _drop_folded_inherited_view(cr)
    _repair_servers(cr)


def _rehome_xmlids(cr):
    moved = 0
    for pattern in XMLID_PATTERNS:
        cr.execute(
            """
                UPDATE ir_model_data d SET module = 'mail'
                 WHERE d.module = 'base'
                   AND d.name LIKE %s
                   AND NOT EXISTS (
                       SELECT 1 FROM ir_model_data e
                        WHERE e.module = 'mail' AND e.name = d.name
                   )
            """,
            (pattern,),
        )
        moved += cr.rowcount
    _logger.info("mail 1.33: %d ir.mail_server xml id(s) re-homed from base", moved)


def _drop_folded_inherited_view(cr):
    cr.execute(
        """
            DELETE FROM ir_ui_view v
                  USING ir_model_data d
                  WHERE d.model = 'ir.ui.view' AND d.res_id = v.id
                    AND d.module = 'mail' AND d.name = 'ir_mail_server_view_form'
              RETURNING v.id
        """
    )
    if cr.rowcount:
        cr.execute(
            "DELETE FROM ir_model_data WHERE module = 'mail' AND name = 'ir_mail_server_view_form'"
        )


def _repair_servers(cr):
    cr.execute(
        """
        UPDATE ir_mail_server
           SET active = FALSE
         WHERE active
           AND smtp_authentication != 'cli'
           AND COALESCE(smtp_host, '') = ''
     RETURNING name
        """
    )
    if archived := [row[0] for row in cr.fetchall()]:
        _logger.warning(
            "Archived %d outgoing mail server(s) saved without an SMTP server "
            "address, which could never have delivered: %s",
            len(archived),
            ", ".join(archived),
        )

    cr.execute(
        """
        UPDATE ir_mail_server
           SET smtp_port = CASE
                   WHEN smtp_encryption IN ('ssl', 'ssl_strict') THEN 465
                   ELSE 25
               END
         WHERE smtp_authentication != 'cli'
           AND (smtp_port IS NULL OR smtp_port < 1 OR smtp_port > 65535)
     RETURNING name
        """
    )
    if reset := [row[0] for row in cr.fetchall()]:
        _logger.warning(
            "Reset the SMTP port of %d outgoing mail server(s) that held a value "
            "outside 1-65535: %s",
            len(reset),
            ", ".join(reset),
        )

    cr.execute(
        """
        UPDATE ir_mail_server
           SET max_email_size = 0
         WHERE max_email_size < 0
     RETURNING name
        """
    )
    if cleared := [row[0] for row in cr.fetchall()]:
        _logger.warning(
            "Cleared the negative maximum email size of %d outgoing mail "
            "server(s), which was stripping every attachment: %s",
            len(cleared),
            ", ".join(cleared),
        )
