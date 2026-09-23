r"""Pre-migration: drop the workflow views that still name the dependency fields.

The predecessor/successor many2many on ``ir.actions.server`` is gone -- a
workflow's shape is now held by ``workflow.edge`` and read through
``edge_in_ids`` / ``edge_out_ids``. ``1.6``'s post-migration is what moves the
rows out of ``ir_action_server_dependency_rel``.

Post is too late for the *views*. ``automation`` loads
``views/ir_actions_server_views.xml`` first, and writing
``automation.view_server_action_form`` revalidates the whole combined arch of
the ``base.view_server_action_form`` it extends -- including the sibling
extension ``view_ir_actions_server_form_workflow_dag``, whose stored arch still
puts ``predecessor_ids`` on the form. Combining them raises `Field
"predecessor_ids" does not exist in model "ir.actions.server"` before any data
file that would have replaced that arch is read, and ``_process_end`` prunes
superseded views only after loading.

All three are still declared by this module and have no views inheriting them,
so deleting the row *and its xmlid* is enough: the data files recreate them
this same upgrade, with the new arch and the same external ids.
"""

import logging
import typing

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)

MODULE = "automation"
SUPERSEDED = (
    "view_ir_actions_server_form_workflow_dag",
    "view_ir_actions_server_tree_workflow",
    "view_automation_runtime_line_form",
)


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return

    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE id IN (
             SELECT res_id FROM ir_model_data
              WHERE model = 'ir.ui.view' AND module = %s AND name = ANY(%s)
         )
        """,
        (MODULE, list(SUPERSEDED)),
    )
    dropped = cr.rowcount

    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE model = 'ir.ui.view' AND module = %s AND name = ANY(%s)
        """,
        (MODULE, list(SUPERSEDED)),
    )

    if dropped:
        _logger.info(
            "Dropped %d superseded workflow view(s); the data files recreate "
            "them without the dependency fields",
            dropped,
        )
