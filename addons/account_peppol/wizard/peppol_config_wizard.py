from markupsafe import Markup

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError


SELF_BILLING_DOCUMENT_TYPES = {
    'bis3_self_billing_invoice': 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0::2.1',
    'bis3_self_billing_credit_note': 'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2::CreditNote##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:selfbilling:3.0::2.1'
}


class PeppolService(models.TransientModel):
    _name = 'account_peppol.service'
    _order = 'document_name, id'
    _description = 'Peppol Service'

    wizard_id = fields.Many2one(comodel_name='peppol.config.wizard')
    document_identifier = fields.Char()
    document_name = fields.Char()
    enabled = fields.Boolean()


class PeppolConfigWizard(models.TransientModel):
    _name = 'peppol.config.wizard'
    _description = "Peppol Configuration Wizard"

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    account_peppol_edi_user = fields.Many2one(related='company_id.account_peppol_edi_user')
    account_peppol_edi_identification = fields.Char(related='account_peppol_edi_user.edi_identification')
    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state', readonly=False)
    account_peppol_contact_email = fields.Char(default=lambda self: self.env.company.account_peppol_contact_email, required=True)
    account_peppol_migration_key = fields.Char(related='company_id.account_peppol_migration_key', readonly=False)
    peppol_activate_self_billing = fields.Boolean(
        string="Activate self-billing",
        help="If activated, you will be able to send and receive self-billed invoices via Peppol."
             "You can still disable reception by disabling the self-billing document types below.",
        compute='_compute_peppol_activate_self_billing',
        inverse='_inverse_peppol_activate_self_billing',
    )
    peppol_self_billing_reception_journal_id = fields.Many2one(related='company_id.peppol_self_billing_reception_journal_id', readonly=False)

    service_json = fields.Json(
        compute='_compute_service_json',
        store=True,
        readonly=False,
        help="JSON representation of peppol services as retrieved from the peppol server.",
    )
    service_info = fields.Html(compute='_compute_service_info')
    service_ids = fields.One2many(
        comodel_name='account_peppol.service',
        inverse_name='wizard_id',
        compute='_compute_service_ids',
        store=True,
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------

    @api.depends('account_peppol_edi_user', 'account_peppol_proxy_state')
    def _compute_service_json(self):
        for wizard in self:
            if wizard.account_peppol_proxy_state == 'receiver':
                try:
                    wizard.service_json = wizard.account_peppol_edi_user._peppol_get_services().get('services')
                except (AccountEdiProxyError, UserError):
                    wizard.service_json = False
            else:
                wizard.service_json = False

    @api.depends('account_peppol_proxy_state')
    def _compute_service_info(self):
        for wizard in self:
            message = ''
            if wizard.account_peppol_proxy_state == 'receiver':
                supported_doctypes = self.env['res.company']._peppol_supported_document_types()
                if (non_configurable := [
                    identifier
                    for identifier in (wizard.service_json or {})
                    if identifier not in supported_doctypes
                ]):
                    message = Markup('%s<ul>%s</ul>') % (
                        _(
                            "The following services are listed on your participant but cannot be configured here. "
                            "If you wish to configure them differently, please contact support."
                        ),
                        Markup().join(
                            Markup('<li>%s</li>') % (wizard.service_json[identifier]['document_name'])
                            for identifier in non_configurable
                        ),
                    )
            wizard.service_info = message

    @api.depends('account_peppol_proxy_state', 'service_json')
    def _compute_service_ids(self):
        """Get the selectable document types.

        Synthesize a combination of locally available document types and those added to the user on
        the IAP, add the relevant services.
        """
        supported_doctypes = self.env['res.company']._peppol_supported_document_types()
        for wizard in self:
            if wizard.account_peppol_proxy_state == 'receiver' and wizard.service_json:
                wizard.service_ids = [
                    Command.create({
                        'document_identifier': identifier,
                        'document_name': document_name,
                        'enabled': identifier in (wizard.service_json or {}),
                        'wizard_id': wizard.id,
                    })
                    for identifier, document_name in supported_doctypes.items()
                ]
            else:
                wizard.service_ids = None

    @api.depends('company_id.peppol_activate_self_billing_sending')
    def _compute_peppol_activate_self_billing(self):
        for wizard in self:
            wizard.peppol_activate_self_billing = wizard.company_id.peppol_activate_self_billing_sending

    @api.onchange('peppol_activate_self_billing')
    def _inverse_peppol_activate_self_billing(self):
        for wizard in self:
            wizard.company_id.peppol_activate_self_billing_sending = wizard.peppol_activate_self_billing

            # When setting the 'Activate self-billing' field, automatically enable/disable the self-billing reception services.
            self_billing_services = wizard.service_ids.filtered(lambda s: s.document_identifier in SELF_BILLING_DOCUMENT_TYPES.values())
            self_billing_services.write({'enabled': wizard.peppol_activate_self_billing})

    def button_sync_form_with_peppol_proxy(self):
        """Update the peppol contact email on IAP.
        Note: The service configuration is DEPRECATED / hidden in the view.
        Disabling services can lead to complicance issues and is not necessary
        since all existing services should just work."""
        self.ensure_one()

        # Update company details
        if self.account_peppol_contact_email != self.company_id.account_peppol_contact_email:
            self.company_id.account_peppol_contact_email = self.account_peppol_contact_email
            params = {
                'update_data': {
                    'peppol_contact_email': self.account_peppol_contact_email,
                }
            }
            self.account_peppol_edi_user._call_peppol_proxy(
                endpoint='/api/peppol/1/update_user',
                params=params,
            )

        return True

    def button_peppol_unregister(self):
        """Unregister the user from Peppol network."""
        self.ensure_one()

        if self.account_peppol_edi_user:
            self.account_peppol_edi_user._peppol_deregister_participant()
        return True
