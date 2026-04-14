import logging
import requests
import secrets
import uuid

from odoo import api, models, fields, tools, modules
from odoo.tools import hash_sign
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vies_valid = fields.Boolean(
        string="Intra-Community Valid",
        compute='_compute_vies_valid', store=True, readonly=False,
        tracking=True,
        help="European VAT numbers are automatically checked on the VIES database.",
    )
    # Field representing whether vies_valid is relevant for selecting a fiscal position on this partner
    perform_vies_validation = fields.Boolean(compute='_compute_perform_vies_validation')

    @api.depends_context('company')
    @api.depends('vat')
    def _compute_perform_vies_validation(self):
        """Determine whether to show VIES validity on the current VAT number"""
        for partner in self:
            to_check = partner.vat
            company_code = self.env.company.account_fiscal_country_id.code
            partner.perform_vies_validation = (
                to_check
                and to_check[:2].upper() != company_code
                and self.env.company.vat_check_vies
            )

    @api.depends('vat')
    def _compute_vies_valid(self):
        """Check the VAT number with VIES, if enabled."""
        if not self.env['res.company'].sudo().search_count([('vat_check_vies', '=', True)]):
            self.vies_valid = False
            return

        for partner in self:
            if not partner.vat:
                partner.vies_valid = False
                continue
            if partner.parent_id and partner.parent_id.vat == partner.vat:
                partner.vies_valid = partner.parent_id.vies_valid
                continue
            status = partner._check_vies_validity_iap()
            partner._update_vies_status(status)

    @api.model
    def _get_iap_vies_credentials(self):
        """
        Return a couple (identifier, token) that is going to identify this db to IAP such that only
        this one can request updates on a previously asked VIES check.
        If they exist, we simply return them. If they don't, we create them in another cursor to
        avoid the current transaction to be rolled back after in case of an uncaucht error while
        the credentials have been registered on IAP.
        """
        # No existing cron = no way for db to pull updates, thus no need to bother IAP
        if (
            not self.env.ref('account_vat_vies.vies_iap_check_update', raise_if_not_found=False)
            or tools.config['test_enable']
            or modules.module.current_test
        ):
            return "dummy_identifier", "dummy_token"  # ignored by IAP, same as neutralized

        IrConfigParam = self.env['ir.config_parameter'].sudo()
        identifier = IrConfigParam.get_str('iap_vies.client_identifier')
        token = IrConfigParam.get_str('iap_vies.client_token')
        if identifier and token:
            return identifier, token

        with self.env.registry.cursor() as new_cursor:
            IrConfigParamNewCursor = self.env(cr=new_cursor)['ir.config_parameter'].sudo()
            identifier = IrConfigParamNewCursor.get_str('iap_vies.client_identifier')
            token = IrConfigParamNewCursor.get_str('iap_vies.client_token')
            if identifier and token:  # recheck existence in case concurrent call by other user for instance
                return identifier, token

            identifier = str(uuid.uuid4())
            token = secrets.token_urlsafe()

            IrConfigParamNewCursor.set_str('iap_vies.client_identifier', identifier)
            IrConfigParamNewCursor.set_str('iap_vies.client_token', token)

        return identifier, token

    @api.model
    def _get_iap_vies_endpoint(self):
        prod, test = 'https://vies.api.odoo.com', 'https://vies.test.odoo.com'
        default_endpoint = test if self.env.ref('base.module_account_vat_vies').demo else prod
        endpoint = self.env['ir.config_parameter'].sudo().get_str('iap_vies.endpoint', default_endpoint)
        if endpoint not in (prod, test):
            raise UserError(self.env._('Invalid IAP VIES endpoint'))
        return endpoint

    def _check_vies_validity_iap(self):
        """Called when VAT is manually edited to query IAP for the validity of the VAT"""
        self.ensure_one()
        endpoint = self._get_iap_vies_endpoint()
        client_identifier, client_token = self._get_iap_vies_credentials()
        try:
            req = requests.post(
                endpoint + '/api/vies/1/check_validity',
                data={
                    'vat': self.vat,
                    'db_uuid': self.env['ir.config_parameter'].sudo().get_str('database.uuid'),
                    'client_identifier': client_identifier,
                    'client_token': client_token,
                    'webhook_url': self.get_base_url() + '/account_vat_vies/1/webhook_update_vies',
                    # See AccountVatViesWebhookController
                    'webhook_token': hash_sign(self.sudo().env, "vies_check", self.vat, expiration_hours=24 * 7),
                },
                timeout=20,
            )
            req.raise_for_status()
        except requests.exceptions.RequestException:
            _logger.exception("VIES check: call to IAP failed")
            return 'fault'
        resp = req.json()
        if not resp.get('status'):
            _logger.error("VIES check: no status returned. Response: %s", resp)
            return 'fault'
        return resp['status']

    @api.model
    def _cron_check_vies_validity_iap(self):
        """Called by cron to check if IAP has any update on a previously requested VAT that was pending"""
        vat_to_status = self._check_vies_update_iap()
        _logger.info("IAP VIES check response: %s", vat_to_status)
        vats = list(vat_to_status)
        grouped_partners = self._read_group(
            domain=[('vat', 'in', vats)],
            groupby=['vat'],
            aggregates=['id:recordset']
        )
        for vat, partners in grouped_partners:
            partners._update_vies_status(vat_to_status[vat])

    def _check_vies_update_iap(self):
        """Calls IAP for an update of a previously requested VAT validity"""
        client_identifier, client_token = self._get_iap_vies_credentials()
        try:
            req = requests.post(
                self._get_iap_vies_endpoint() + '/api/vies/1/check_update',
                data={
                    'db_uuid': self.env['ir.config_parameter'].sudo().get_str('database.uuid'),
                    'client_identifier': client_identifier,
                    'client_token': client_token,
                },
                timeout=10,
            )
            req.raise_for_status()
            return req.json()
        except requests.exceptions.RequestException:
            _logger.exception("Error while contacting IAP VIES")
        return {}

    def _update_vies_status(self, status):
        self.vies_valid = status == 'valid'
        _logger.info("VIES status updated to %s for partner ids: %s", status, self.ids)
        msg = None
        if status == 'pending':
            msg = self.env._("The VIES check is pending. The status will be updated soon.")
        elif status == 'fault':
            msg = self.env._("The VIES check failed. Please check the Tax ID manually.")
        elif status in ('valid', 'unassigned'):
            msg = self.env._("The Intra-Community validity has been updated to: %s.", status)
        if msg:
            self._message_log_batch(bodies={p._origin.id: msg for p in self if p._origin.id})

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if self.env.context.get('import_file'):
            res.env.remove_to_compute(self._fields['vies_valid'], res)
        return res

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('import_file'):
            self.env.remove_to_compute(self._fields['vies_valid'], self)
        return res

    def _create_contact_parent_company(self, values):
        new_company = super()._create_contact_parent_company(values)
        if new_company and self.vies_valid:
            new_company.env.remove_to_compute(self._fields['vies_valid'], new_company)
            new_company.vies_valid = self.vies_valid
        return new_company
