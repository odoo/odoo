from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.addons.base.models.res_partner_bank import sanitize_account_number

ACCOUNT_DOCUMENT_LAYOUT_COMPANY_FIELDS = {
    'logo',
    'report_header',
    'report_footer',
    'company_details',
    'paperformat_id',
    'font',
    'primary_color',
    'secondary_color',
    'report_tables_id',
    'qr_code',
    'vat',
}


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    from_invoice = fields.Boolean()
    qr_code = fields.Boolean(related='company_id.qr_code', readonly=False)
    vat = fields.Char(related='company_id.vat', readonly=False,)
    account_number = fields.Char(compute='_compute_account_number', inverse='_inverse_account_number',)
    country_code = fields.Char(related="company_id.account_fiscal_country_id.code")
    can_configure_later = fields.Boolean(compute='_compute_can_configure_later')

    def _check_company_access(self, companies):
        allowed_company_ids = self.env.companies.ids
        if (
            not companies
            or any(company.id not in allowed_company_ids for company in companies)
        ):
            raise AccessError(
                self.env._("You cannot configure the document layout for this company.")
            )

    def _get_accessible_preview_move(self):
        self.ensure_one()
        if (
            self.env.context.get('active_model') != 'account.move'
            or not self.env.context.get('active_id')
        ):
            return self.env['account.move']

        move = self.env['account.move'].browse(
            self.env.context['active_id']
        ).exists()
        if not move:
            raise AccessError(self.env._("You cannot preview this invoice."))

        move.check_access('read')
        if move.company_id != self.company_id:
            raise AccessError(self.env._("You cannot preview this invoice."))

        return move

    def document_layout_save(self):
        """Save layout and onboarding step progress, return super() result"""
        res = super(BaseDocumentLayout, self).document_layout_save()
        if step := self.env.ref('account.onboarding_onboarding_step_base_document_layout', raise_if_not_found=False):
            for company_id in self.company_id:
                # Account users cannot write the technical onboarding progress records so we must use sudo.
                step.sudo().with_company(company_id).action_set_just_done()
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

    def _is_account_layout_configurator(self):
        return (
            self.env.context.get('account_document_layout_configurator')
            and self.env.user.has_group('account.group_account_basic')
        )

    @api.depends('partner_id', 'account_number')
    def _compute_account_number(self):
        for record in self:
            if record.partner_id.bank_ids:
                record.account_number = record.partner_id.bank_ids[0].account_number or ''
            else:
                record.account_number = ''

    @api.depends('qr_code', 'account_number')
    def _compute_preview(self):
        # EXTENDS 'web' - Re-trigger preview rendering when invoice-specific fields change.

        # Safely route any non-account wizards to the base method.
        non_account_wizards = self.filtered(lambda w: not w._is_account_layout_configurator())
        super(BaseDocumentLayout, non_account_wizards)._compute_preview()

        account_wizards = self - non_account_wizards
        if not account_wizards:
            return

        styles = self._get_asset_style()
        for wizard in account_wizards:
            wizard._check_company_access(wizard.company_id)

            if not wizard.report_layout_id:
                wizard.preview = False
                continue

            render_information = wizard._get_render_information(styles)
            if preview_move := wizard._get_accessible_preview_move():
                render_information['o'] = preview_move

            wizard.preview = self.env['ir.ui.view']._render_template(
                wizard._get_preview_template(),
                render_information,
            )

    @api.depends_context('can_configure_later')
    def _compute_can_configure_later(self):
        can_configure_later = bool(self.env.context.get('can_configure_later'))
        for wizard in self:
            wizard.can_configure_later = can_configure_later

    def _inverse_account_number(self):
        for record in self:
            if record.partner_id.bank_ids and record.account_number:
                bank = record.partner_id.bank_ids[0]
                cleaned_account_number = sanitize_account_number(record.account_number)
                if bank.account_number != cleaned_account_number:
                    bank.allow_out_payment = False
                    bank.account_number = record.account_number
                    bank.allow_out_payment = True
            elif record.account_number:
                record.partner_id.bank_ids += self.env['res.partner.bank']._find_or_create_bank_account(
                    account_number=record.account_number,
                    partner=record.partner_id, allow_company_account_creation=True,
                    company=record.company_id,
                )

    @api.model
    def _extract_company_layout_vals(self, vals):
        vals.pop('external_report_layout_id', None)

        company_vals = {}
        for field_name in ACCOUNT_DOCUMENT_LAYOUT_COMPANY_FIELDS:
            if field_name in vals:
                company_vals[field_name] = vals.pop(field_name)

        if 'report_layout_id' in vals:
            report_layout = self.env['report.layout'].browse(vals['report_layout_id'])
            company_vals['external_report_layout_id'] = report_layout.view_id.id if report_layout else False

        return company_vals

    @api.onchange('company_id')
    def _onchange_company_id(self):
        account_wizards = self.filtered(lambda w: w._is_account_layout_configurator())

        super(BaseDocumentLayout, self - account_wizards)._onchange_company_id()

        if account_wizards:
            for wizard in account_wizards:
                wizard._check_company_access(wizard.company_id)

            # Call super() as sudo since account users cannot read the ir.ui.view referenced by external_report_layout_id.
            super(BaseDocumentLayout, account_wizards.sudo())._onchange_company_id()

    def _get_asset_style(self):
        if not self._is_account_layout_configurator():
            return super()._get_asset_style()

        return self.env['ir.qweb'].sudo()._render('web.styles_company_report', {
            'company_ids': self.sudo(),
        }, raise_if_not_found=False)

    @api.model_create_multi
    def create(self, vals_list):
        if not self._is_account_layout_configurator():
            return super().create(vals_list)

        self.check_access('create')
        vals_list = [dict(vals) for vals in vals_list]
        companies = []
        company_vals_list = []

        for vals in vals_list:
            company = self.env['res.company'].browse(
                vals.get('company_id') or self.env.company.id
            )
            self._check_company_access(company)
            vals['company_id'] = company.id

            companies.append(company)
            company_vals_list.append(self._extract_company_layout_vals(vals))

        records = super(BaseDocumentLayout, self.sudo()).create(vals_list).with_env(self.env)

        for company, company_vals in zip(companies, company_vals_list):
            if company_vals:
                company.sudo().write(company_vals)

        return records

    def write(self, vals):
        if not self._is_account_layout_configurator():
            return super().write(vals)

        vals = dict(vals)
        companies = (
            self.env['res.company'].browse(vals['company_id'])
            if 'company_id' in vals
            else self.company_id
        )
        self._check_company_access(companies)

        company_vals = self._extract_company_layout_vals(vals)

        res = super().write(vals)

        if company_vals:
            companies.sudo().write(company_vals)

        return res

    def action_configure_later(self):
        self.ensure_one()
        report_action = self.env.context.get('report_action')
        if not report_action:
            return {'type': 'ir.actions.act_window_close'}

        self.check_access('write')
        self._check_company_access(self.company_id)
        self.company_id.sudo().external_report_layout_id = False
        return report_action
