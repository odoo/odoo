from markupsafe import Markup

from odoo import api, Command, fields, models, _


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
                wizard.service_json = wizard.account_peppol_edi_user._peppol_get_services().get('services')
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

    @api.depends('account_peppol_proxy_state')
    def _compute_service_ids(self):
        """Get the selectable document types.

        Synthesize a combination of locally available document types and those added to the user on
        the IAP, add the relevant services.
        """
        supported_doctypes = self.env['res.company']._peppol_supported_document_types()
        for wizard in self:
            if wizard.account_peppol_proxy_state == 'receiver':
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

    def button_sync_form_with_peppol_proxy(self):
        """Interpret changes to the services, and add or remove them on the IAP accordingly."""
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

        # Update services
        if self.account_peppol_proxy_state == 'receiver':
            services = self.service_ids.read(['document_identifier', 'enabled'])
            service_json = self.service_json or {}
            to_add, to_remove = [], []

            for service in services:
                if service['document_identifier'] in service_json and not service['enabled']:
                    to_remove.append(service['document_identifier'])

                if service['document_identifier'] not in service_json and service['enabled']:
                    to_add.append(service['document_identifier'])

            if to_add:
                self.account_peppol_edi_user._call_peppol_proxy(
                    "/api/peppol/2/add_services", {
                        'document_identifiers': to_add,
                    },
                )
            if to_remove:
                self.account_peppol_edi_user._call_peppol_proxy(
                    "/api/peppol/2/remove_services", {
                        'document_identifiers': to_remove,
                    },
                )

        return True

    def button_peppol_unregister(self):
        """Unregister the user from Peppol network."""
        self.ensure_one()

        if self.account_peppol_edi_user:
            self.account_peppol_edi_user._peppol_deregister_participant()
        return True
