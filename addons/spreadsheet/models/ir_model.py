from odoo import api, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.readonly
    @api.model
    def has_searchable_parent_relation(self, model_names):
        result = {}
        for model_name in model_names:
            model = self.env.get(model_name)
            if model is None or not model.has_access("read"):
                result[model_name] = False
            else:
                # we consider only stored parent relationships were meant to
                # be searched
                result[model_name] = (
                    model._parent_store and model._parent_name in model._fields
                )
        _debug.pipeline(
            "spreadsheet_parent_relations_checked",
            models=len(model_names),
            searchable=sum(1 for value in result.values() if value),
        )
        return result
