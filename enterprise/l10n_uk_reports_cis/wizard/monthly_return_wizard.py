from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning


class MontlhyReturnWizard(models.TransientModel):
    _name = "cis.monthly.return.wizard"
    _description = "CIS monthly return wizard"

    date_from = fields.Date(string="Date From")
    date_to = fields.Date(string="Date To")
    subcontractor_verification = fields.Boolean(string="Subcontractor Verification")
    employment_status = fields.Boolean(string="Employment Status")
    inactivity_indicator = fields.Boolean(string="Inactivity Indicator")
    information_correct = fields.Boolean(string="Information Correct")
    hmrc_cis_password = fields.Char(string="CIS password", store=False)
    use_wrong_period = fields.Boolean(string="Use Wrong Password")
    already_submited_period = fields.Boolean(string="Already Submited Period")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        options = self.env.context.get('options')
        if not options:
            return res
        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])

        if 'date_from' in fields_list:
            res['date_from'] = date_from

        if 'date_to' in fields_list:
            res['date_to'] = date_to

        if 'use_wrong_period' in fields_list:
            if options['date']['period_type'] != 'tax_period':
                period_start, period_end = self.env.company._get_tax_closing_period_boundaries(date_to, self.env.ref('l10n_uk_reports_cis.tax_report_cis'))
                res['use_wrong_period'] = period_start != date_from or period_end != date_to
            else:
                res['use_wrong_period'] = False

        if 'already_submited_period' in fields_list:
            res['already_submited_period'] = self.env['l10n_uk.hmrc.transaction'].search_count([
                ('company_id.id', '=', self.env.company.id),
                ('period_start', '=', date_from),
                ('period_end', '=', date_to),
                ('state', 'in', ('polling', 'success', 'deleted')),
            ], limit=1) > 0

        return res

    @api.model
    def action_send_montlhy_return(self, date_from, date_to, employment_status, subcontractor_verification, inactivity_indicator, hmrc_cis_password):
        cis_report = self.env.ref('l10n_uk_reports_cis.tax_report_cis')

        if not self.env.company.l10n_uk_hmrc_unique_taxpayer_reference or not self.env.company.l10n_uk_hmrc_account_office_reference:
            raise RedirectWarning(
                message=_("Please fill the CIS fields on the company."),
                action={
                    'view_mode': 'form',
                    'res_model': 'res.company',
                    'type': 'ir.actions.act_window',
                    'res_id': self.env.company.id,
                    'views': [(False, 'form')],
                },
                button_text=_("Open the company form"),
            )

        # Ensure that `export_mode` is set to `file` so we use default groupby and don't display comparison
        options = cis_report.get_options({'export_mode': 'file'})
        options['date'].update({
            'date_from': date_from,
            'date_to': date_to,
        })
        lines = cis_report._get_lines(options)

        # The report gives us the lines for sales and purchase.
        # The CIS deduction monthly return is a document made by contractor for subcontractors to HMRC.
        # So in this case we only need the purchase part of the report
        cis_purchase_report_line_id = self.env.ref('l10n_uk_reports_cis.account_uk_cis_report_line_purchase').id
        partner_lines = [
            line for line in lines
            if line['groupby'] == 'move_id'
                and self.env['account.report']._get_res_id_from_line_id(line['id'], 'account.report.line') == cis_purchase_report_line_id
        ]

        document_data = {
            'inactivity_indicator': inactivity_indicator,
            'subcontractor_return_ids': [],
            'subcontractor_ids': [],
            'subcontractor_verification': subcontractor_verification,
            'employment_status': employment_status,
        }

        for partner_line in partner_lines:
            colname_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
            partner_id = cis_report._get_res_id_from_line_id(partner_line['id'], 'res.partner')
            document_data['subcontractor_return_ids'].append({
                'id': partner_id,
                'total_payment_made': partner_line['columns'][colname_to_idx['payment']].get('no_format', 0.0),
                'direct_cost_of_materials': partner_line['columns'][colname_to_idx['materials']].get('no_format', 0.0),
                'total_amount_deducted': partner_line['columns'][colname_to_idx['deduction']].get('no_format', 0.0),
            })
            document_data['subcontractor_ids'].append(partner_id)

        transaction = self.env['l10n_uk.hmrc.transaction'].create({
            'transaction_type': 'cis_monthly_return',
            'period_start': date_from,
            'period_end': date_to,
            'company_id': self.env.company.id,
            'sender_user_id': self.env.user.id,
        })

        transaction.sudo()._submit_cis_mr_transaction(
            credentials={
                'sender_id': self.env.company.l10n_uk_hmrc_sender_id,
                'password': hmrc_cis_password,
                'tax_office_number': self.env.company.l10n_uk_hmrc_tax_office_number,
                'tax_office_reference': self.env.company.l10n_uk_hmrc_tax_office_reference,
            },
            document_data=document_data,
        )
