# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from stdnum.exceptions import InvalidFormat, InvalidLength
from stdnum.nl.btw import validate

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class VATPayWizard(models.TransientModel):
    _name = 'l10n_nl.vat.pay.wizard'
    _description = "Payment instructions for VAT"

    move_id = fields.Many2one(comodel_name='account.move', readonly=True)
    company_currency_id = fields.Many2one(related='move_id.company_currency_id')
    amount = fields.Monetary(currency_field='company_currency_id')
    partner_bank_id = fields.Many2one(comodel_name='res.partner.bank', compute='_compute_partner_bank_id')
    acc_number = fields.Char(string="IBAN", related='partner_bank_id.acc_number')
    partner_id = fields.Many2one(comodel_name='res.partner', related='partner_bank_id.partner_id')
    communication = fields.Char(compute='_compute_communication')
    qr_code = fields.Html(compute='_compute_qr_code')

    @api.depends('move_id')
    def _compute_communication(self):
        for wizard in self:
            company = wizard.move_id.company_id or self.env.company
            try:
                vat = validate(company._get_nl_vat())
            except Exception as e:
                raise UserError(_(
                    "Something went wrong while validating the VAT number: %s. You can modify it in the company settings.",
                    company.vat
                )) from e
            head, tail = vat.split("B")
            date = wizard.move_id.date

            # For a trimester-based tax period, adjust the date to the start of the trimester by subtracting 2 months.
            if company.account_tax_periodicity == 'trimester':
                date -= relativedelta(months=2)

            period_code_map = {
                'monthly': f'{date.month:02}',
                'trimester': f'{20 + date.month}',
                'year': '40',
            }

            if company.account_tax_periodicity not in period_code_map:
                raise UserError(_(
                    "Invalid tax periodicity. Please use one of the following: %s.",
                    ', '.join(
                        label
                        for value, label in company._fields['account_tax_periodicity']._description_selection(self.env)
                        if value in period_code_map
                    )
                ))

            block_1 = f"{head[:3]}"
            block_2 = f"{head[3:7]}"
            block_3 = f"{head[7:8]}1{str(date.year)[-1]}{tail[0]}"
            block_4 = f"{tail[1]}{period_code_map[company.account_tax_periodicity]}0"
            blocks = [block_1, block_2, block_3, block_4]

            checksum = self._l10n_nl_get_modulo_11_checksum("".join(blocks))
            wizard.communication = checksum + ".".join(blocks)

    def _l10n_nl_get_modulo_11_checksum(self, number):
        """
        Calculates the Modulo 11 checksum for a given numeric string using a predefined set of weights.

        The function iterates over each digit in the input string from right to left, applying the corresponding weight
        in a cyclic manner. The checksum is computed as the weighted sum of the digits modulo 11.

        Source: https://www.betaalvereniging.nl/betalingsverkeer/giraal-betalingsverkeer/betalingskenmerken/specificaties-nl-betalingskenmerk/

        :param str number: A string representing a numeric input for which the checksum needs to be calculated.
        :returns: The Modulo 11 checksum as a string.
            Returns '0' or '1' if the remainder is 0 or 1,
            otherwise returns the complement of the remainder (i.e., 11 - remainder).
        :rtype: str.
        """
        n = len(number)
        weights = [2, 4, 8, 5, 10, 9, 7, 3, 6, 1]
        remainder = sum(int(number[n - i - 1]) * weights[i % len(weights)] for i in range(n)) % 11

        if remainder in (0, 1):
            return str(remainder)

        return str(11 - remainder)

    @api.depends('move_id')
    def _compute_partner_bank_id(self):
        belastingdienst_account = self.env.ref('l10n_nl_reports_vat_pay_wizard.belastingdienst_current_account', raise_if_not_found=False)
        if not belastingdienst_account:
            raise UserError(_(
                "The Belastingdienst account is not configured."
                "Please update module 'l10n_nl_reports_vat_pay_wizard'."
            ))
        self.partner_bank_id = belastingdienst_account

    @api.depends('communication', 'amount')
    def _compute_qr_code(self):
        for wizard in self:
            qr_html = False
            if wizard.partner_bank_id and wizard.amount and wizard.communication:
                b64_qr = wizard.partner_bank_id.build_qr_code_base64(
                    amount=wizard.amount,
                    free_communication=wizard.communication,
                    structured_communication=wizard.communication,
                    currency=wizard.company_currency_id or self.env.company.currency_id,
                    debtor_partner=wizard.partner_id,
                )
                if b64_qr:
                    txt = _('Scan me with your banking app.')
                    qr_html = Markup("""
                        <div class="text-center">
                            <img src="{b64_qr}"/>
                            <p><strong>{txt}</strong></p>
                        </div>
                    """).format(b64_qr=b64_qr, txt=txt)
            wizard.qr_code = qr_html

    def mark_paid(self):
        activity = self.move_id.activity_ids.filtered(lambda a: a.activity_type_id == self.env.ref('account_reports.mail_activity_type_tax_report_to_pay'))
        activity.action_done()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
