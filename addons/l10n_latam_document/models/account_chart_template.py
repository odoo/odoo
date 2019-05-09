# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    @api.multi
    def _load_template(
            self, company, code_digits=None, account_ref=None, taxes_ref=None):
        """ Set localization to company when installing chart of account.
        """
        self.ensure_one()
        self._generate_receiptbooks(company)
        return super(AccountChartTemplate, self)._load_template(
            company, code_digits, account_ref, taxes_ref)

    @api.model
    def _generate_receiptbooks(self, company):
        """ Overwrite this function so that no journal is created on chart
        installation
        """
        if company._localization_use_documents():
            receiptbook_data = self._prepare_all_receiptbook_data(company)
            for receiptbook_vals in receiptbook_data:
                self._check_created_receiptbooks(receiptbook_vals, company)
        return True

    @api.model
    def _check_created_receiptbooks(self, receiptbook_vals, company):
        """ This method used for checking new receipbooks already created or
        not. If not then create new receipbook.
        """
        receipbook = self.env['l10n_latam.payment.receiptbook'].search([
            ('name', '=', receiptbook_vals['name']),
            ('company_id', '=', company.id)])
        if not receipbook:
            receipbook.create(receiptbook_vals)
        return True

    @api.model
    def _prepare_all_receiptbook_data(self, company):
        """ This method can be inherited by different localizations
        """
        receiptbook_data = []
        partner_type_name_map = {
            'customer': _('%s Customer Receipts'),
            'supplier': _('%s Supplier Payments'),
        }
        sequence_types = {
            'automatic': _('Automatic'),
            'manual': _('Manual'),
        }
        # we use for sequences and for prefix
        sequences = {
            'automatic': 1,
            'manual': 2,
        }
        for sequence_type in ['automatic', 'manual']:
            for partner_type in ['supplier', 'customer']:
                document_type = self.env['l10n_latam.document.type'].search([
                    ('internal_type', '=', '%s_payment' % partner_type)
                ], limit=1)
                if not document_type:
                    continue
                vals = {
                    'name': partner_type_name_map[partner_type] % (
                        sequence_types[sequence_type]),
                    'partner_type': partner_type,
                    'sequence_type': sequence_type,
                    'padding': 8,
                    'company_id': company.id,
                    'document_type_id': document_type.id,
                    'prefix': (
                        '%%0%sd-' % 4 % sequences[sequence_type]),
                    'sequence': sequences[sequence_type],
                }
                receiptbook_data.append(vals)
        return receiptbook_data

    @api.model
    def _prepare_all_journals(
            self, acc_template_ref, company, journals_dict=None):
        """ We add use_documents or not depending on the context
        """
        journal_data = super(
            AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict)

        # if chart has localization, then we use documents by default
        if company._localization_use_documents():
            for vals_journal in journal_data:
                if vals_journal['type'] in ['sale', 'purchase']:
                    vals_journal['l10n_latam_use_documents'] = True
        return journal_data
