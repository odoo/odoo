from odoo import api, Command, fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    from_invoice = fields.Boolean()
    qr_code = fields.Boolean(related='company_id.qr_code', readonly=False)
    vat = fields.Char(related='company_id.vat', readonly=False,)
    account_number = fields.Char(compute='_compute_account_number', inverse='_inverse_account_number',)

    def document_layout_save(self):
        """Save layout and onboarding step progress, return super() result"""
        res = super(BaseDocumentLayout, self).document_layout_save()
        if step := self.env.ref('account.onboarding_onboarding_step_base_document_layout', raise_if_not_found=False):
            for company_id in self.company_id:
                step.with_company(company_id).action_set_just_done()
            # When we finish the configuration of the layout, we want the dialog size to be reset to large
            # which is the default behaviour.
            if res.get('context'):
                res['context']['dialog_size'] = 'large'
        return res

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
            and (active_id := self.env.context.get('active_id'))
        ):
            res['o'] = self.env['account.move'].browse(active_id)

        if self._get_preview_template() in [
            'web.report_invoice_wizard_preview',
            'account.report_invoice_wizard_iframe'
        ]:
            res.update({
                'qr_code': self.qr_code,
                'account_number': self.account_number,
            })

        return res

    @api.depends('partner_id', 'account_number')
    def _compute_account_number(self):
        for record in self:
            if record.partner_id.bank_ids:
                record.account_number = record.partner_id.bank_ids[0].acc_number or ''
            else:
                record.account_number = ''

    @api.depends('qr_code', 'account_number')
    def _compute_preview(self):
        # EXTENDS 'web' to add dependencies
        super()._compute_preview()

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
