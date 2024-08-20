from odoo import api, Command, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    from_invoice = fields.Boolean()
    qr_code = fields.Boolean(related='company_id.qr_code', readonly=False)
    vat = fields.Char(related='company_id.vat', readonly=False,)
    account_number = fields.Char(compute='_compute_account_number', inverse='_inverse_account_number',)

    def _get_preview_template(self):
        if (
            self.env.context.get('active_model') == 'account.move'
            and self.env.context.get('active_id')
        ):
            return 'account.report_invoice_wizard_iframe'
        return super()._get_preview_template()

    def _get_render_information(self, styles):
        res = super()._get_render_information(styles)
        if (
            self.env.context.get('active_model') == 'account.move'
            and self.env.context.get('active_id')
        ):
            res.update({
                'o': self.env['account.move'].browse(self.env.context.get('active_id')),
                'qr_code': self.qr_code,
            })
        return res

    @api.depends('partner_id', 'account_number')
    def _compute_account_number(self):
        for record in self:
            if record.partner_id.bank_ids:
                record.account_number = record.partner_id.bank_ids[0].acc_number or ''
            else:
                record.account_number = ''

    def _inverse_account_number(self):
        for record in self:
            if record.partner_id.bank_ids and record.account_number:
                record.partner_id.bank_ids[0].acc_number = record.account_number
            elif record.account_number:
                record.partner_id.bank_ids = [
                    Command.create({
                        'acc_number': record.account_number,
                        'partner_id': record.partner_id.id,
                    })
                ]
