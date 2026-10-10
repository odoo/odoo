from collections import defaultdict

from odoo import _, api, fields, models

from odoo.addons.l10n_tr_edi.const import L10N_TR_GIB_ALLOWED_NUMS


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('ubl_tr', "Türkiye (UBL TR 1.2)")])
    l10n_tr_edi_customer_status = fields.Selection(
        selection=[
            ('not_checked', "Not Verified"),
            ('earchive', "E-Archive"),
            ('einvoice', "E-Invoice"),
        ],
        string="GİB Status",
        copy=False,
        default='not_checked',
        readonly=True,
        tracking=True,
        help="Whether the partner is registered with the GİB for e-Invoices, or receives e-Archive invoices.",
    )

    l10n_tr_edi_alias_ids = fields.One2many(
        comodel_name='l10n_tr_edi.alias',
        inverse_name="partner_id",
        help="The GİB aliases of the partner, used to address the electronic documents sent to it.",
    )
    l10n_tr_edi_einvoice_alias_id = fields.Many2one(
        comodel_name='l10n_tr_edi.alias',
        string="eInvoice Alias",
        compute='_compute_l10n_tr_edi_einvoice_alias_id',
        domain="[('partner_id', '=', id)]",
        copy=False,
        store=True,
        readonly=False,
        help="Specifies the GİB alias of the partner, used when sending electronic invoices. \n"
        "It helps make sure your customer is correctly recognized by the GİB when e-invoices are sent. \n"
        "This ID is needed for your invoices to be processed correctly and comply with Turkish tax rules.",
    )

    @api.depends('l10n_tr_edi_alias_ids', 'l10n_tr_edi_customer_status')
    def _compute_l10n_tr_edi_einvoice_alias_id(self):
        for record in self:
            if record.l10n_tr_edi_customer_status == 'einvoice' and not record.l10n_tr_edi_einvoice_alias_id:
                record.l10n_tr_edi_einvoice_alias_id = record.l10n_tr_edi_alias_ids[:1]
            elif record.l10n_tr_edi_customer_status == 'earchive':
                record.l10n_tr_edi_einvoice_alias_id = False

    @api.depends('invoice_edi_format')
    def _compute_is_company(self):
        # Any partner that has the ubl_tr invoicing format set will be categorized as follows
        # A company has a 10-digit or less Tax ID (VKN) & an individual contact has an 11-digit or more Tax ID (TCKN)
        l10n_tr_partners = self.env['res.partner']
        for partner in self:
            if partner.invoice_edi_format != "ubl_tr":
                continue
            partner.is_company = False
            if partner.has_vat and partner.vat.isdigit() and len(partner.vat) <= 10:
                partner.is_company = True
            l10n_tr_partners += partner

        super(ResPartner, self - l10n_tr_partners)._compute_is_company()

    def check_vat_tr(self, vat):
        # EXTENDS 'base'
        return super().check_vat_tr(vat) or vat in L10N_TR_GIB_ALLOWED_NUMS

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        res = super()._get_suggested_invoice_edi_format()
        if self.country_code == 'TR':
            return 'ubl_tr'
        return res

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_tr':
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_tr'] = {'countries': ['TR']}
        return formats_info

    def _l10n_tr_edi_send_user_notification(self, type, message, action_button=None):
        self.env.user._bus_send(
            'account_notification' if action_button else 'simple_notification',
            {
                'type': type,
                'message': message,
                'action_button': action_button,
            }
        )

    def action_l10n_tr_edi_verify_customer_status(self):
        results = defaultdict(lambda: self.env['res.partner'])
        # we want to skip records whose status is already set, unless we want to
        # purposefully retry them
        retry_existing = self.env.context.get('retry_existing', False)
        for record in self.filtered(lambda p: p.vat and p.invoice_edi_format and (retry_existing or p.l10n_tr_edi_customer_status == 'not_checked')):
            if record._l10n_tr_edi_fetch_customer_status():
                if len(record.l10n_tr_edi_alias_ids) > 1:
                    results['multi_alias'] |= record
                else:
                    results['success'] |= record
            else:
                results['failure'] |= record

        if results['failure']:
            self._l10n_tr_edi_send_user_notification('danger', self.env._("GİB status verification failed. Please try again."))
        if results['success']:
            self._l10n_tr_edi_send_user_notification('success', self.env._("GİB status verified successfully."))
        if multi_alias := results['multi_alias']:
            self._l10n_tr_edi_send_user_notification(
                'warning',
                _('Multiple alias entries were found for the following partners. Please verify the correct one manually.'),
                action_button={
                    'name': _('View Partners'),
                    'action_name': _('Partners in Error'),
                    'model': 'res.partner',
                    'res_ids': multi_alias.ids,
                },
            )

    def _l10n_tr_edi_fetch_customer_status(self):
        """Ask the company's e-Document provider whether the partner receives e-Invoices or
        e-Archives, and update `l10n_tr_edi_customer_status` accordingly.

        Without a provider there is nobody to ask, so the status is left untouched. Provider
        modules override this when the company uses them.

        :return: whether the provider answered.
        """
        self.ensure_one()
