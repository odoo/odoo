# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
from lxml import etree
from hashlib import md5
from urllib import parse

from odoo import api, fields, models

TIMEOUT = 10

class ResPartner(models.Model):
    _inherit = 'res.partner'

    account_peppol_is_endpoint_valid = fields.Boolean(
        string="PEPPOL endpoint validity",
        help="The partner's EAS code and PEPPOL endpoint are valid",
        compute="_compute_account_peppol_is_endpoint_valid", store=True,
        copy=False,
    )
    account_peppol_validity_last_check = fields.Date(
        string="Checked on",
        help="Last Peppol endpoint verification",
        readonly=True,
        copy=False,
    )
    account_peppol_verification_label = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Not valid'),
            ('valid', 'Valid'),
        ],
        string='Peppol endpoint validity',
        compute='_compute_account_peppol_verification_label',
        copy=False,
    ) # field to compute the label to show for partner endpoint

    @api.depends('peppol_eas', 'peppol_endpoint')
    def _compute_account_peppol_is_endpoint_valid(self):
        # Every change in peppol_eas or peppol_endpoint should set the validity back to False
        self.account_peppol_is_endpoint_valid = False

    @api.depends('account_peppol_is_endpoint_valid', 'account_peppol_validity_last_check')
    def _compute_account_peppol_verification_label(self):
        for partner in self:
            if not partner.account_peppol_validity_last_check:
                partner.account_peppol_verification_label = 'not_verified'
            elif partner.account_peppol_is_endpoint_valid:
                partner.account_peppol_verification_label = 'valid'
            else:
                partner.account_peppol_verification_label = 'not_valid'

    def button_account_peppol_check_partner_endpoint(self):
        """ A basic check for whether a participant is reachable at the given
        Peppol participant ID - peppol_eas:peppol_endpoint (ex: '9999:test')
        The SML (Service Metadata Locator) assigns a DNS name to each peppol participant.
        This DNS name resolves into the SMP (Service Metadata Publisher) of the participant.
        The DNS address is of the following form:
        - "http://B-" + hexstring(md5(lowercase(ID-VALUE))) + "." + ID-SCHEME + "." + SML-ZONE-NAME + "/" + url_encoded(ID-SCHEME + "::" + ID-VALUE)
        (ref:https://peppol.helger.com/public/locale-en_US/menuitem-docs-doc-exchange)
        """
        self.ensure_one()

        participant = f'{self.peppol_eas}:{self.peppol_endpoint}'.lower()
        hash_participant = md5(participant.lower().encode()).hexdigest()
        endpoint_participant = parse.quote_plus(f"iso6523-actorid-upis::{participant}")
        peppol_param = self.env['ir.config_parameter'].sudo().get_param('account_peppol.edi.mode', False)
        sml_zone = 'acc.edelivery' if peppol_param == 'test' else 'edelivery'
        smp_url = f"http://B-{hash_participant}.iso6523-actorid-upis.{sml_zone}.tech.ec.europa.eu/{endpoint_participant}"
        self.account_peppol_validity_last_check = fields.Date.context_today(self)
        try:
            response = requests.get(smp_url, timeout=TIMEOUT)
        except requests.exceptions.ConnectionError:
            self.account_peppol_is_endpoint_valid = False
        else:
            if response.status_code != 200:
                self.account_peppol_is_endpoint_valid = False
                return

            participant_info = etree.XML(response.content)
            participant_identifier = participant_info.find('{*}ParticipantIdentifier').text
            if participant != participant_identifier:
                self.account_peppol_is_endpoint_valid = False
                return

            self.account_peppol_is_endpoint_valid = True
