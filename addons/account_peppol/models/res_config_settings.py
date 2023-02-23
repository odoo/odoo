# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo import api, fields, models, _
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.exceptions import UserError, ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_peppol_eas = fields.Selection(related='company_id.peppol_eas', readonly=False)
    account_peppol_endpoint = fields.Char(related='company_id.peppol_endpoint', readonly=False)
    account_peppol_proxy_state = fields.Selection(related='company_id.account_peppol_proxy_state')
    account_peppol_purchase_journal_id = fields.Many2one(related='company_id.peppol_purchase_journal_id', readonly=False)
    account_peppol_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string='Peppol Identification Documents',
        related='company_id.account_peppol_attachment_ids', readonly=False,
    )
    is_account_peppol_eligible = fields.Boolean(
        string='PEPPOL eligible',
        compute='_compute_is_account_peppol_eligible',
    ) # technical field used for showing the Peppol settings conditionally
    is_account_peppol_participant = fields.Boolean(
        string='Use PEPPOL',
        related='company_id.is_account_peppol_participant', readonly=False,
        help='Register as a PEPPOL user',
    )

    @api.depends("company_id.country_id")
    def _compute_is_account_peppol_eligible(self):
        # we want to show Peppol settings only to BE and LU customers at first
        # but keeping an option to see them for testing purposes using a config param
        for config in self:
            peppol_param = config.env['ir.config_parameter'].sudo().get_param(
                'account_peppol.edi.mode', False
            )
            config.is_account_peppol_eligible = config.company_id.country_id.code in {'BE', 'LU'} \
                or peppol_param == 'test'

    def button_create_peppol_proxy_user(self):
        self.ensure_one()

        if self.account_peppol_proxy_state != 'not_registered':
            raise UserError(
                _('Cannot register a user with a %s application', self.account_peppol_proxy_state))

        if not self.company_id.account_peppol_attachment_ids:
            raise ValidationError(
                _('Please upload a document that would help verifying your application'))
        edi_proxy_client = self.env['account_edi_proxy_client.user']
        edi_identification = edi_proxy_client._get_proxy_identification(self.company_id)
        edi_user = edi_proxy_client.sudo()._register_proxy_user(
            self.company_id, 'peppol', 'prod', edi_identification)

        params = {'documents': []}
        for attachment in self.company_id.account_peppol_attachment_ids:
            params['documents'].append((attachment.name, b64encode(attachment.raw).decode()))

        try:
            response = edi_user._make_request(
                f"{edi_user._get_server_url()}/api/peppol/1/activate_participant",
                params=params,
            )
        except AccountEdiProxyError as e:
            raise UserError(e.message)
        if 'error' in response:
            raise UserError(response['error'])

        self.company_id.account_peppol_proxy_state = 'pending'
        # we don't need to store the attachments once they've been sent to the proxy
        self.company_id.account_peppol_attachment_ids.unlink()
