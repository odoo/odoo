from odoo import api, fields, models


class Test_ConvertUsered(models.Model):
    _name = "test_convert.usered"
    _description = "z test model ignore"

    name = fields.Char()
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
    )
    test_id = fields.Many2one(comodel_name="test_convert.test_model")
    tz = fields.Char(
        default=lambda self: self.env.context.get("tz") or self.env.user.tz
    )

    @api.model
    def model_method(self, *args, **kwargs):
        return self, args, kwargs

    def method(self, *args, **kwargs):
        return self, args, kwargs
