# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, _
from openerp.tools.misc import formatLang


class ReportL10nBePartnerVatListing(models.AbstractModel):
    _name = "l10n.be.report.partner.vat.listing"
    _description = "Partner VAT Listing"

    @api.model
    def get_lines(self, context_id, line_id=None):
        lines = []

        partner_ids = self.env['res.partner'].search([('vat_subjected', '!=', False), ('vat', 'ilike', 'BE%')]).ids
        if not partner_ids:
            return lines
        tag_ids = [self.env['ir.model.data'].xmlid_to_res_id(k) for k in ['l10n_be.tax_tag_base_00', 'l10n_be.tax_tag_base_01', 'l10n_be.tax_tag_base_02', 'l10n_be.tax_tag_base_03', 'l10n_be.tax_tag_base_45']]
        tag_ids_2 = [self.env['ir.model.data'].xmlid_to_res_id(k) for k in ['l10n_be.tax_tag_base_01', 'l10n_be.tax_tag_base_02', 'l10n_be.tax_tag_base_03']]
        self.env.cr.execute("""SELECT sub1.partner_id, sub1.name, sub1.vat, sub1.turnover, sub2.vat_amount
            FROM (SELECT l.partner_id, p.name, p.vat, SUM(l.balance) as turnover
                  FROM account_move_line l
                  LEFT JOIN res_partner p ON l.partner_id = p.id
                  LEFT JOIN account_move_line_account_tax_rel amlt ON l.id = amlt.account_move_line_id
                  LEFT JOIN account_tax_account_tag tt on amlt.account_tax_id = tt.account_tax_id
                  WHERE tt.account_account_tag_id IN %s
                  AND l.partner_id IN %s
                  AND l.date >= %s
                  AND l.date <= %s
                  GROUP BY l.partner_id, p.name, p.vat) AS sub1
            LEFT JOIN (SELECT l2.partner_id, SUM(l2.balance) as vat_amount
                  FROM account_move_line l2
                  LEFT JOIN account_tax_account_tag tt2 on l2.tax_line_id = tt2.account_tax_id
                  WHERE tt2.account_account_tag_id IN %s
                  AND l2.partner_id IN %s
                  AND l2.date > %s
                  AND l2.date < %s
                  GROUP BY l2.partner_id) AS sub2 ON sub1.partner_id = sub2.partner_id
                """, (tuple(tag_ids), tuple(partner_ids), context_id.date_from, context_id.date_to, tuple(tag_ids_2), tuple(partner_ids), context_id.date_from, context_id.date_to))
        for record in self.env.cr.dictfetchall():
            columns = [record['vat'].replace(' ', '').upper(), record['turnover'], record['vat_amount']]
            if not self.env.context.get('no_format', False):
                currency_id = self.env.user.company_id.currency_id
                columns[1] = formatLang(self.env, columns[1], currency_obj=currency_id)
                columns[2] = formatLang(self.env, columns[2], currency_obj=currency_id)
            lines.append({
                'id': record['partner_id'],
                'type': 'partner_id',
                'name': record['name'],
                'footnotes': context_id._get_footnotes('partner_id', record['partner_id']),
                'columns': columns,
                'level': 2,
                'unfoldable': False,
                'unfolded': False,
            })
        return lines

    @api.model
    def get_title(self):
        return _('Partner VAT Listing')

    @api.model
    def get_name(self):
        return 'l10n_be_partner_vat_listing'

    @api.model
    def get_report_type(self):
        return 'no_comparison'

    @api.model
    def get_template(self):
        return 'account_reports.report_financial'


class ReportL10nBePartnerVatListingContext(models.TransientModel):
    _name = "l10n.be.partner.vat.listing.context"
    _description = "A particular context for the generic tax report"
    _inherit = "account.report.context.common"

    def get_report_obj(self):
        return self.env['l10n.be.report.partner.vat.listing']

    @api.multi
    def remove_line(self, line_id):
        return

    @api.multi
    def add_line(self, line_id):
        return

    def get_columns_names(self):
        return [_('VAT Number'), _('Turn Over'), _('VAT Amount')]

    @api.multi
    def get_columns_types(self):
        return ['text', 'number', 'number']
