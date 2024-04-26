from odoo import api, Command, fields, models
from odoo.tools import is_html_empty


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

    @api.depends('qr_code')
    def _compute_preview(self):
        """ This override is needed to add the depends on the qr code and the move """
        super()._compute_preview()
        if self.env.context.get('active_model') != 'account.move':
            return
        move = self.env['account.move'].browse(self.env.context.get('active_id'))
        # If there is a move in the context then, the value put in the preview come from the move
        if not move.exists():
            return

        styles = self._get_asset_style()
        for wizard in self:
            if wizard.report_layout_id:
                preview_css, wizard_with_logo = wizard._get_render_information(styles)

                # We don't want to display the qr_code twice since we decided to put a fake one.
                move.display_qr_code = False
                wizard.preview = wizard_with_logo.env['ir.ui.view']._render_template('account.report_invoice_wizard_iframe', {
                    'company': wizard_with_logo,
                    'preview_css': preview_css,
                    'is_html_empty': is_html_empty,
                    'o': move,
                    'qr_code': wizard.qr_code,
                })

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
