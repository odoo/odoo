from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MixinHierarchy(models.AbstractModel):
    _name = "mixin.hierarchy"
    _description = "Hierarchy (a parent/child tree kept on a materialized path)"
    _parent_store = True

    _hierarchy_cycle_message = None

    parent_path = fields.Char(index=True)

    @api.constrains(lambda self: [self._parent_name])
    def _check_parent_id(self):
        if self._has_cycle():
            _debug.logic("hierarchy_cycle", model=self._name, count=len(self))
            raise ValidationError(
                self._hierarchy_cycle_message
                or self.env._("A record cannot be its own ancestor.")
            )
