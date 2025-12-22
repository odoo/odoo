# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo import osv
from odoo.tools.sql import SQL
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
                name = _("%(tag)s (%(country_code)s)", tag=tag.name, country_code=tag.country_id.code)
            tag.display_name = name

    @api.model_create_multi
    def create(self, vals_list):
        tags = super().create(vals_list)
        if tax_tags := tags.filtered(lambda tag: tag.applicability == 'taxes'):
            self._translate_tax_tags(tag_ids=tax_tags.ids)
        return tags

    @api.model
    def _get_tax_tags(self, tag_name, country_id):
        """ Returns all the tax tags corresponding to the tag name given in parameter
        in the specified country.
        """
        domain = self._get_tax_tags_domain(tag_name, country_id)
        original_lang = self._context.get('lang', 'en_US')
        rslt_tags = self.env['account.account.tag'].with_context(active_test=False, lang='en_US').search(domain)
        return rslt_tags.with_context(lang=original_lang)  # Restore original language, in case the name of the tags needs to be shown/modified

    @api.model
    def _get_tax_tags_domain(self, tag_name, country_id, sign=None):
        """ Returns a domain to search for all the tax tags corresponding to the tag name given in parameter
        in the specified country.
        """
        escaped_tag_name = tag_name.replace('\\', '\\\\').replace('%', r'\%').replace('_', r'\_')
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

    def _translate_tax_tags(self, langs=None, tag_ids=None):
        """Translate tax tags having the same name as report lines."""
        langs = langs or (code for code, _name in self.env['res.lang'].get_installed() if code != 'en_US')
        for lang in langs:
            self.env.cr.execute(SQL(
                """
                UPDATE account_account_tag tag
                   SET name = tag.name || jsonb_build_object(%(lang)s, substring(tag.name->>'en_US' FOR 1) || (report_line.name->>%(lang)s))
                  FROM account_report_line report_line
                  JOIN account_report report ON report.id = report_line.report_id
                 WHERE tag.applicability = 'taxes'
                   AND tag.country_id = report.country_id
                   AND tag.name->>'en_US' = substring(tag.name->>'en_US' FOR 1) || (report_line.name->>'en_US')
                   AND tag.name->>%(lang)s != substring(tag.name->>'en_US' FOR 1) || (report_line.name->>%(lang)s)
                   %(and_tag_ids)s
                """,
                lang=lang,
                and_tag_ids=SQL('AND tag.id IN %s', tuple(tag_ids)) if tag_ids else SQL(''),
            ))
