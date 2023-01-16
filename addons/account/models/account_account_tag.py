# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAccountTag(models.Model):
    _name = 'account.account.tag'
    _description = 'Account Tag'

    name = fields.Char('Tag Name', required=True)
    applicability = fields.Selection([('accounts', 'Accounts'), ('taxes', 'Taxes'), ('products', 'Products')], required=True, default='accounts')
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True, help="Set active to false to hide the Account Tag without removing it.")
    tax_report_line_ids = fields.Many2many(string="Tax Report Lines", comodel_name='account.tax.report.line', relation='account_tax_report_line_tags_rel', help="The tax report lines using this tag")
    tax_negate = fields.Boolean(string="Negate Tax Balance", help="Check this box to negate the absolute value of the balance of the lines associated with this tag in tax report computation.")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="Country for which this tag is available, when applied on taxes.")

    @api.model
    def _get_tax_tags(self, tag_name, country_id):
        """ Returns all the tax tags corresponding to the tag name given in parameter
        in the specified country.
        """
        escaped_tag_name = tag_name.replace('\\', '\\\\').replace('%', '\%').replace('_', '\_')
        domain = [('name', '=like', '_' + escaped_tag_name), ('country_id', '=', country_id), ('applicability', '=', 'taxes')]
        return self.env['account.account.tag'].with_context(active_test=True).search(domain)
