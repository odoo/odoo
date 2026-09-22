from . import const
from . import models
from . import reports
from . import tools
from . import wizards


def pre_init_hook(env):
    env["ir.model.data"].search(
        [("model", "like", "stock"), ("module", "=", "stock")]
    ).unlink()


def uninstall_hook(env):
    picking_type_ids = (
        env["stock.picking.type"].with_context({"active_test": False}).search([])
    )
    picking_type_ids.sequence_id.unlink()
