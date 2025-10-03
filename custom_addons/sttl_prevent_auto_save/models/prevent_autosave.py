from odoo import api, fields, models


class PreventModel(models.Model):
    _name = "prevent.model"
    _description = "Prevent Model"

    auto_save_prevent = fields.Boolean("Prevent Auto Save for Specific Model")
    auto_save_prevent_all = fields.Boolean("Prevent Auto Save Globally")
    model_ids = fields.One2many('prevent.model.line', 'prevent_id', "Select Model")

    @api.onchange('auto_save_prevent')
    def onchange_method_auto_save_prevent(self):
        if self.auto_save_prevent:
            self.auto_save_prevent_all = False

    @api.onchange('auto_save_prevent_all')
    def onchange_method_auto_save_prevent_all(self):
        if self.auto_save_prevent_all:
            self.auto_save_prevent = False


class PreventModelLine(models.Model):
    _name = "prevent.model.line"
    _description = "Prevent Model Line"

    model_id = fields.Many2one('ir.model', "Model ID")
    model_description = fields.Char(related="model_id.name", string="Description")
    model = fields.Char(related="model_id.model", string="Model")
    prevent_id = fields.Many2one('prevent.model', string="Prevent Model Id")
