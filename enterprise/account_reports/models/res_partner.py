# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    account_represented_company_ids = fields.One2many('res.company', 'account_representative_id')

    def _get_followup_responsible(self):
        return self.env.user

    def open_partner_ledger(self):
        # Deprecated, will be removed in master
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_partner_ledger")
        action['params'] = {
            'options': {'partner_ids': self.ids, 'unfold_all': len(self.ids) == 1},
            'ignore_session': True,
        }
        return action

    def open_customer_statement(self):
        if not self.env.ref('account_reports.customer_statement_report', raise_if_not_found=False):
            return self.open_partner_ledger()
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_customer_statement")
        action['params'] = {
            'options': {
                'partner_ids': (self | self.commercial_partner_id).ids,
                'unfold_all': len(self.ids) == 1,
            },
            'ignore_session': True,
        }
        return action

    def open_partner(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'views': [[False, 'form']],
            'view_mode': 'form',
            'target': 'current',
        }

    @api.depends_context('show_more_partner_info')
    def _compute_display_name(self):
        if not self.env.context.get('show_more_partner_info'):
            return super()._compute_display_name()
        for partner in self:
            res = ""
            if partner.vat:
                res += f" {partner.vat},"
            if partner.country_id:
                res += f" {partner.country_id.code},"
            partner.display_name = f"{partner.name} - " + res

    def _get_partner_account_report_attachment(self, report, options=None):
        self.ensure_one()
        if self.lang:
            # Print the followup in the customer's language
            report = report.with_context(lang=self.lang)

        if not options:
            options = report.get_options({
                'forced_companies': self.env.company.search([('id', 'child_of', self.env.context.get('allowed_company_ids', self.env.company.id))]).ids,
                'partner_ids': self.ids,
                'unfold_all': True,
                'unreconciled': True,
                # The following two options are Deprecated, will be removed in master
                'hide_account': True,
                'hide_debit_credit': True,
                'all_entries': False,
            })
        attachment_file = report.export_to_pdf(options)
        return self.env['ir.attachment'].create([
            {
                'name': f"{self.name} - {attachment_file['file_name']}",
                'res_model': self._name,
                'res_id': self.id,
                'type': 'binary',
                'raw': attachment_file['file_content'],
                'mimetype': 'application/pdf',
            },
        ])

    def set_commercial_partner_main(self):
        self.ensure_one()

        main_partner = self
        duplicated_partners = self.env['res.partner'].search([
            ('vat', '=', main_partner.vat),
            ('id', '!=', main_partner.id)
        ])
        # Update commercial partner of all duplicates
        duplicated_partners.write({
            'is_company': False,
            'parent_id': main_partner.id,
            'type': 'invoice',
        })
        duplicated_partners_vat = self._context.get('duplicated_partners_vat', [])
        remaining_vats = [pvat for pvat in duplicated_partners_vat if pvat != main_partner.vat]
        return self.env['account.ec.sales.report.handler']._get_duplicated_vat_partners(remaining_vats)
