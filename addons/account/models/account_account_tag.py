# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo import osv
from odoo.exceptions import UserError


class AccountAccountTag(models.Model):
    _name = 'account.account.tag'
    _description = 'Account Tag'

    name = fields.Char('Tag Name', required=True, translate=True)
    applicability = fields.Selection([('accounts', 'Accounts'), ('taxes', 'Taxes'), ('products', 'Products')], required=True, default='accounts')
    color = fields.Integer('Color Index')
    active = fields.Boolean(default=True, help="Set active to false to hide the Account Tag without removing it.")
    tax_negate = fields.Boolean(string="Negate Tax Balance", help="Check this box to negate the absolute value of the balance of the lines associated with this tag in tax report computation.")
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="Country for which this tag is available, when applied on taxes.")

    _sql_constraints = [('name_uniq', "unique(name, applicability, country_id)", "A tag with the same name and applicability already exists in this country.")]

    @api.depends('applicability', 'country_id')
    @api.depends_context('company')
    def _compute_display_name(self):
        if not self.env.company.multi_vat_foreign_country_ids:
            return super()._compute_display_name()

        for tag in self:
            name = tag.name
            if tag.applicability == "taxes" and tag.country_id and tag.country_id != self.env.company.account_fiscal_country_id:
                name = _("%s (%s)", tag.name, tag.country_id.code)
            tag.display_name = name

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

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_tags(self):
        master_xmlids = [
            "account_tag_operating",
            "account_tag_financing",
            "account_tag_investing",
        ]
        for master_xmlid in master_xmlids:
            master_tag = self.env.ref(f"account.{master_xmlid}", raise_if_not_found=False)
            if master_tag and master_tag in self:
                raise UserError(_("You cannot delete this account tag (%s), it is used on the chart of account definition.", master_tag.name))
