import requests
from lxml import etree
from hashlib import md5
from urllib import parse

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_dk_nemhandel.tools.demo_utils import handle_demo

TIMEOUT = 10

class ResPartner(models.Model):
    _inherit = 'res.partner'

    nemhandel_verification_state = fields.Selection(
        selection=[
            ('not_verified', 'Not verified yet'),
            ('not_valid', 'Not valid'),  # does not exist on Nemhandel
            ('valid', 'Valid'),
        ],
        default='not_verified',
        string='Nemhandel endpoint verification',
        copy=False,
        tracking=True,
    )

    nemhandel_identifier_type = fields.Selection(
        string="Nemhandel endpoint type",
        help="Unique identifier used by OIOUBL and Nemhandel",
        tracking=True,
        selection=[
            ('0088', "EAN/GLN"),
            ('0184', "CVR"),
            ('9918', "IBAN"),
            ('0198', "SE"),
        ],
    )
    nemhandel_identifier_value = fields.Char(
        string="Nemhandel EAS",
        help="Code used to identify the Endpoint on Nemhandel and OIOUBL",
        tracking=True,
    )

    ubl_cii_format = fields.Selection(selection_add=[('oioubl_21', "OIOUBL 2.1")])

    def _get_edi_builder(self):
        if self.ubl_cii_format == 'oioubl_21':
            return self.env['account.edi.xml.oioubl_21']
        return super()._get_edi_builder()

    @api.depends('country_code')
    def _compute_ubl_cii_format(self):
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'DK':
                partner.ubl_cii_format = 'oioubl_21'

    @api.model
    def _get_nemhandel_participant_info(self, edi_identification):
        hash_participant = md5(edi_identification.lower().encode()).hexdigest()
        endpoint_participant = parse.quote_plus(f"iso6523-actorid-upis::{edi_identification}")
        nemhandel_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'nemhandel')
        edi_mode = nemhandel_user and nemhandel_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.edi.mode')
        sml_zone = 'edel.sml-demo' if edi_mode == 'test' else 'edel.sml'
        smp_url = f"http://B-{hash_participant}.iso6523-actorid-upis.{sml_zone}.dataudveksling.dk/{endpoint_participant}"
        try:
            response = requests.get(smp_url, timeout=TIMEOUT)
        except requests.exceptions.ConnectionError:
            return None
        if response.status_code != 200:
            return None
        return etree.fromstring(response.content)

    @api.model
    def _check_nemhandel_participant_exists(self, participant_info, edi_identification):
        participant_identifier = participant_info.findtext('{*}ParticipantIdentifier')
        service_metadata = participant_info.find('.//{*}ServiceMetadataReference')
        if service_metadata is None:
            return False
        service_href = service_metadata.attrib.get('href', '')
        nemhandel_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'nemhandel')
        edi_mode = nemhandel_user and nemhandel_user.edi_mode or self.env['ir.config_parameter'].sudo().get_param('l10n_dk_nemhandel.edi.mode')
        smp_nemhandel_url = 'http://smp-demo.nemhandel.dk' if edi_mode == 'test' else 'http://smp.nemhandel.dk'

        return edi_identification == participant_identifier and service_href.startswith(smp_nemhandel_url)

    @handle_demo
    def button_nemhandel_check_partner_endpoint(self):
        """ A basic check for whether a participant is reachable at the given identifier_type and identifier_value
        """
        self.ensure_one()

        if not self.nemhandel_identifier_type or not self.nemhandel_identifier_value:
            self.nemhandel_verification_state = 'not_verified'
        else:
            nemhandel_user = self.env.company.sudo().account_edi_proxy_client_ids.filtered(lambda user: user.proxy_type == 'nemhandel')
            edi_identification = f'{self.nemhandel_identifier_type}:{self.nemhandel_identifier_value}'
            resp = nemhandel_user._call_nemhandel_proxy(
                endpoint='/api/nemhandel/1/participant_exists',
                params={'edi_identification': edi_identification},
            )
            if 'code' in resp:
                # NHR PORS returned an error on this participant
                self.nemhandel_verification_state = 'not_valid'
                return False
            participant_info = self._get_nemhandel_participant_info(edi_identification)
            if participant_info is None:
                self.nemhandel_verification_state = 'not_valid'
            else:
                self.nemhandel_verification_state = 'valid' if self._check_nemhandel_participant_exists(participant_info, edi_identification) else 'not_valid'
        return False
