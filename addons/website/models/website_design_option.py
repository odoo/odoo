from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class WebsiteDesignOption(models.Model):
    _name = 'website.design.option'
    _description = 'Website Design Option'

    name = fields.Char(string='Name', required=True)
    value = fields.Char(string='Value')
    display_name = fields.Char(string='Display Name')
    # When an option is set as a design value, we activate views defined in the
    # following field and deactivate views defined in the following field where
    # the name is equal but the value is different.
    views_to_activate = fields.Many2many(string='Views to Activate', comodel_name='ir.ui.view')
    assets_to_activate = fields.Many2many(string='Assets to Activate', comodel_name='ir.asset')

    _sql_constraints = [
        ('name_value_unique', 'UNIQUE(name, value)', 'The combination of name and value already exists!'),
    ]

    @api.model
    def create(self, vals):
        design_fields = self.env['website.design']._fields
        name = vals.get('name')
        if name not in design_fields or design_fields[name].comodel_name != 'website.design.option':
            raise ValidationError(_("%s have to be a website.design field referencing a website.design.option.", name))
        return super(WebsiteDesignOption, self).create(vals)
