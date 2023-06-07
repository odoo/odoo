# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo import osv


class AccountAccountTag(models.Model):
    _name = 'account.account.tag'
    _description = 'Account Tag'

    name = fields.Char('Tag Name', required=True)
    applicability = fields.Selection([('accounts', 'Accounts'), ('taxes', 'Taxes'), ('products', 'Products')], required=True, default='accounts')
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True, help="Set active to false to hide the Account Tag without removing it.")
    tax_negate = fields.Boolean(string="Negate Tax Balance", help="Check this box to negate the absolute value of the balance of the lines associated with this tag in tax report computation.")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="Country for which this tag is available, when applied on taxes.")

    def name_get(self):
        if not self.env.company.multi_vat_foreign_country_ids:
            return super().name_get()

        res = []
        for tag in self:
            name = tag.name
            if tag.applicability == "taxes" and tag.country_id and tag.country_id != self.env.company.account_fiscal_country_id:
                name = _("%s (%s)", tag.name, tag.country_id.code)
            res.append((tag.id, name,))

        return res

    @api.model
    def _get_tax_tags(self, tag_name, country_id):
        """ Returns all the tax tags corresponding to the tag name given in parameter
        in the specified country.
        """
        domain = self._get_tax_tags_domain(tag_name, country_id)
        return self.env['account.account.tag'].with_context(active_test=False).search(domain)

    @api.model
    def _get_tax_tags_domain(self, tag_name, country_id, sign=None):
        """ Returns a domain to search for all the tax tags corresponding to the tag name given in parameter
        in the specified country.
        """
        escaped_tag_name = tag_name.replace('\\', '\\\\').replace('%', '\%').replace('_', '\_')
        return [
            ('name', '=like', (sign or '_') + escaped_tag_name),
            ('country_id', '=', country_id),
            ('applicability', '=', 'taxes')
        ]

    def _get_related_tax_report_expressions(self):
        if not self:
            return self.env['account.report.expression']

        or_domains = []
        for record in self:
            expr_domain = [
                '&',
                ('report_line_id.report_id.country_id', '=', record.country_id.id),
                ('formula', '=', record.name[1:]),
            ]
            or_domains.append(expr_domain)

        domain = osv.expression.AND([[('engine', '=', 'tax_tags')], osv.expression.OR(or_domains)])
        return self.env['account.report.expression'].search(domain)
