# -*- coding: utf-8 -*-
from odoo import fields, models, _


class AccountReportFileDownloadErrorWizard(models.TransientModel):
    _name = 'account.report.file.download.error.wizard'
    _description = "Manage the file generation errors from report exports."

    file_generation_errors = fields.Json()
    file_name = fields.Char()
    file_content = fields.Binary()

    def button_download(self):
        self.ensure_one()
        if self.file_name:
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/account.report.file.download.error.wizard/{self.id}/file_content/{self.file_name}?download=1',
                'close': True,
            }

    def action_open_partners(self, partner_ids):
        self.ensure_one()
        return {
            'name': _('Invalid Partners'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'domain': [('id', '=', partner_ids)],
            'view_mode': 'list',
            'views': [(False, 'list'), (False, 'form')],
        }

    def action_open_partner_company(self, company_id):
        self.ensure_one()
        return {
            'name': _('Missing Company Data'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': company_id,
            'views': [(False, 'form')],
        }

    def action_open_settings(self, company_id):
        self.ensure_one()
        return {
            'name': _('Settings'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.config.settings',
            'views': [(False, 'form')],
            'context': {'module': 'account', 'bin_size': False},
        }

    def action_open_taxes(self, tax_ids):
        self.ensure_one()
        return {
            'name': _('Invalid Taxes'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.tax',
            'domain': [('id', '=', tax_ids)],
            'view_mode': 'list',
            'views': [(False, 'list'), (False, 'form')],
        }

    def action_open_products(self, product_ids):
        self.ensure_one()
        return {
            'name': _('Invalid Products'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'domain': [('id', '=', product_ids)],
            'view_mode': 'list',
            'views': [(False, 'list'), (False, 'form')],
        }
