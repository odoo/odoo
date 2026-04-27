from odoo import api, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    @api.model
    def _is_valid_for_model_selector(self, model):
        return model not in {
            # bank.rec.widget* does not have a psql table with _auto=False & _table_query="0",
            # which makes the models unusable in the model selector.
            'bank.rec.widget',
            'bank.rec.widget.line',
        } and super()._is_valid_for_model_selector(model)
