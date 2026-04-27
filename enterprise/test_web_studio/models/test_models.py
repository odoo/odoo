from odoo import models, fields


class ModelAction(models.Model):
    _name = "test.studio.model_action"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Test Model Studio"

    name = fields.Char()
    confirmed = fields.Boolean()
    step = fields.Integer()
    partner_id = fields.Many2one("res.partner")

    def action_confirm(self):
        for rec in self:
            rec.confirmed = True

    def action_step(self):
        for rec in self:
            rec.step = rec.step + 1


class ModelAction2(models.Model):
    _inherit = "test.studio.model_action"
    _name = "test.studio.model_action2"
    _description = "Test Model Studio 2"


class Model1(models.Model):
    _name = "test.studio_export.model1"
    _description = "Test Model for Studio Exports 1"
    name = fields.Char()
    attachment_id = fields.Many2one("ir.attachment")
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[("res_model", "=", "test.studio_export.model1")],
        string="Attachments",
    )
    binary_data = fields.Binary()
    model2_id = fields.Many2one("test.studio_export.model2")


class Model2(models.Model):
    _name = "test.studio_export.model2"
    _description = "Test Model for Studio Exports 2"
    name = fields.Char()
    model2_id = fields.Many2one("test.studio_export.model2")
    model3_id = fields.Many2one("test.studio_export.model3")
    res_model = fields.Char()
    res_id = fields.Many2oneReference(model_field="res_model")


class Model3(models.Model):
    _name = "test.studio_export.model3"
    _description = "Test Model for Studio Exports 3"
    name = fields.Char()
    model1_id = fields.Many2one("test.studio_export.model1")
