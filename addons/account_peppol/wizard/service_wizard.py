# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from markupsafe import Markup

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PeppolService(models.TransientModel):
    _name = 'account_peppol.service'
    _order = 'document_name, id'
    _description = 'Peppol Service'

    wizard_id = fields.Many2one(comodel_name='account_peppol.service.wizard')
    document_identifier = fields.Char()
    document_name = fields.Char()
    enabled = fields.Boolean()


class PeppolServiceConfig(models.TransientModel):
    _name = 'account_peppol.service.wizard'
    _description = 'Peppol Services Wizard'

    edi_user_id = fields.Many2one(comodel_name='account_edi_proxy_client.user', string='EDI user')
    service_json = fields.Json(help="JSON representation of peppol services as retrieved from the peppol server.")
    service_info = fields.Html(compute='_compute_service_info')
    service_ids = fields.One2many(
        comodel_name='account_peppol.service',
        inverse_name='wizard_id',
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------

    def _compute_service_info(self):
        for wizard in self:
            message = ''
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

    # -------------------------------------------------------------------------
    # OVERRIDES
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Get the selectable document types.

        Synthesize a combination of locally available document types and those added to the user on
        the IAP, add the relevant services.
        """
        wizards = super().create(vals_list)
        supported_doctypes = self.env['res.company']._peppol_supported_document_types()
        for wizard in wizards:
            wizard.service_ids.create([
                {
                    'document_identifier': identifier,
                    'document_name': document_name,
                    'enabled': identifier in (wizard.service_json or {}),
                    'wizard_id': wizard.id,
                }
                for identifier, document_name in supported_doctypes.items()
            ])
        return wizards

    def confirm(self):
        """Interpret changes to the services, and add or remove them on the IAP accordingly."""
        services = self.service_ids.read(['document_identifier', 'enabled'])
        service_json = self.service_json or {}
        to_add, to_remove = [], []

        for service in services:
            if service['document_identifier'] in service_json and not service['enabled']:
                to_remove.append(service['document_identifier'])

            if service['document_identifier'] not in service_json and service['enabled']:
                to_add.append(service['document_identifier'])

        if to_add:
            self.edi_user_id._call_peppol_proxy(
                "/api/peppol/2/add_services", {
                    'document_identifiers': to_add,
                },
            )
        if to_remove:
            self.edi_user_id._call_peppol_proxy(
                "/api/peppol/2/remove_services", {
                    'document_identifiers': to_remove,
                },
            )
