from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_tr_edi.const import L10N_TR_GIB_ALLOWED_NUMS


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('ubl_tr', "Türkiye (UBL TR 1.2)")])
    l10n_tr_edi_customer_status = fields.Selection(
        selection=[
            ('not_checked', "Not Verified"),
            ('earchive', "e-Archive"),
            ('einvoice', "e-Invoice"),
        ],
        string="GİB Status",
        copy=False,
        default='not_checked',
        readonly=True,
        tracking=True,
        help="Whether the partner is registered with the GİB for e-Invoices, or receives e-Archive invoices.",
    )
    l10n_tr_edi_einvoice_alias = fields.Char(
        string="e-Invoice Alias",
        copy=False,
        readonly=True,
        help="The GİB alias (mailbox) of the partner, used when sending electronic invoices. \n"
        "It is picked among the aliases the GİB lists for the partner, with the button next to it.",
    )

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
        if not self.env.company.l10n_tr_edi_provider:
            # Nobody can answer without a provider: say so rather than report a failed check to retry.
            self._l10n_tr_edi_send_user_notification(
                'warning', self.env._("No e-Document provider is set, so the GİB status cannot be verified."),
            )
            return
        results = defaultdict(lambda: self.env['res.partner'])
        # we want to skip records whose status is already set, unless we want to
        # purposefully retry them
        retry_existing = self.env.context.get('retry_existing', False)
        for record in self.filtered(lambda p: p.vat and p.invoice_edi_format and (retry_existing or p.l10n_tr_edi_customer_status == 'not_checked')):
            aliases = record._l10n_tr_edi_fetch_customer_status()
            if aliases is not None:
                try:
                    record._l10n_tr_edi_verify_other_aliases()
                except UserError:
                    aliases = None
            if aliases is None:
                results['failure'] |= record
            elif len(aliases) > 1:
                results['multi_alias'] |= record
            else:
                results['success'] |= record

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
        modules override this when the company uses them, recording the answer with
        `_l10n_tr_edi_set_customer_status`.

        :return: the names of the partner's e-Invoice aliases, empty for an e-Archive user, or None when nobody
                 answered.
        """
        self.ensure_one()

    def _l10n_tr_edi_set_customer_status(self, aliases):
        """Record the provider's answer about the partner: an e-Invoice user receiving at `aliases`, or an e-Archive
        user when there are none.

        The e-Invoice alias is kept while the GİB still lists it, else the first one listed is taken, so a partner
        can be invoiced right after its check; another one is picked with the alias button.

        :param aliases: the names of the partner's e-Invoice aliases at the GİB, in the provider's order.
        """
        self.ensure_one()
        if not aliases:
            self.write({'l10n_tr_edi_customer_status': 'earchive', 'l10n_tr_edi_einvoice_alias': False})
            return
        values = {'l10n_tr_edi_customer_status': 'einvoice'}
        if self.l10n_tr_edi_einvoice_alias not in aliases:
            values['l10n_tr_edi_einvoice_alias'] = aliases[0]
        self.write(values)

    def _l10n_tr_edi_verify_other_aliases(self):
        """Refresh the partner's aliases for the documents other than invoices, once its GİB status is verified.

        Modules sending other documents extend this, fetching the aliases with `_l10n_tr_edi_fetch_aliases`.
        """
        self.ensure_one()

    def action_l10n_tr_edi_select_einvoice_alias(self):
        return self._l10n_tr_edi_action_select_alias('einvoice')

    def _l10n_tr_edi_action_select_alias(self, alias_type):
        """Open the wizard picking the partner's alias of `alias_type` among those its provider lists now.

        :param alias_type: the kind of document the alias receives, a `l10n_tr_edi.alias.wizard` alias type.
        """
        self.ensure_one()
        wizard = self.env['l10n_tr_edi.alias.wizard']
        aliases = self._l10n_tr_edi_fetch_aliases(alias_type)
        if not aliases:
            raise UserError(self.env._(
                "The GİB lists no %(alias_type)s alias for %(partner)s.",
                alias_type=dict(wizard._fields['alias_type']._description_selection(self.env))[alias_type],
                partner=self.display_name,
            ))
        wizard = wizard.create({
            'partner_id': self.id,
            'alias_type': alias_type,
            'alias_ids': [Command.create({'name': alias}) for alias in aliases],
        })
        return {
            'name': self.env._("Choose a GİB Alias"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': wizard._name,
            'res_id': wizard.id,
            'target': 'new',
        }

    def _l10n_tr_edi_fetch_aliases(self, alias_type):
        """Return the names of the partner's aliases of `alias_type` that the company's e-Document provider lists.

        Provider modules override this when the company uses them.

        :param alias_type: the kind of document the alias receives, a `l10n_tr_edi.alias.wizard` alias type.
        """
        self.ensure_one()
        raise UserError(self.env._("No e-Document provider is set, so the GİB aliases cannot be fetched."))
