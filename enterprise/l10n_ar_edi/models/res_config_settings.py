import re

from odoo import _, fields, models
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    l10n_ar_afip_verification_type = fields.Selection(related='company_id.l10n_ar_afip_verification_type', readonly=False)

    l10n_ar_afip_ws_environment = fields.Selection(related='company_id.l10n_ar_afip_ws_environment', readonly=False)
    l10n_ar_afip_ws_key_id = fields.Many2one(related='company_id.l10n_ar_afip_ws_key_id', readonly=False)
    l10n_ar_afip_ws_crt_id = fields.Many2one(related='company_id.l10n_ar_afip_ws_crt_id', readonly=False)

    l10n_ar_fce_transmission_type = fields.Selection(related="company_id.l10n_ar_fce_transmission_type", readonly=False)
    l10n_ar_payment_foreign_currency = fields.Selection(
        related="company_id.l10n_ar_payment_foreign_currency",
        readonly=False,
        inverse="_inverse_l10n_ar_payment_foreign_currency")

    def l10n_ar_action_create_certificate_request(self):
        self.ensure_one()
        if not self.company_id.partner_id.city:
            raise UserError(_('The company city must be defined before this action'))
        if not self.company_id.partner_id.country_id:
            raise UserError(_('The company country must be defined before this action'))
        if not self.company_id.partner_id.l10n_ar_vat:
            raise UserError(_('The company CUIT must be defined before this action'))

        if not self.l10n_ar_afip_ws_key_id:
            private_key_sudo = self.env['certificate.key'].sudo()._generate_rsa_private_key(self.company_id, name='afip_id_rsa_%s' % fields.Datetime.now().strftime("%Y%m%d_%H%M%S"))
            self.l10n_ar_afip_ws_key_id = private_key_sudo

        return {'type': 'ir.actions.act_url', 'url': '/l10n_ar_edi/download_csr/' + str(self.company_id.id), 'target': 'new'}

    def l10n_ar_connection_test(self):
        self.ensure_one()
        errors = []
        if not self.l10n_ar_afip_ws_crt_id:
            errors.append(_("Please set a certificate in order to make the test"))
        if not self.l10n_ar_afip_ws_key_id:
            errors.append(_("Please set a private key in order to make the test"))
        if errors:
            raise UserError("\n* ".join(errors))

        results = []
        for webservice in [item[0] for item in self.env["l10n_ar.afipws.connection"]._get_l10n_ar_afip_ws()]:
            try:
                self.company_id._l10n_ar_get_connection(webservice)
                results.append(_("* %(webservice)s: Connection is available", webservice=webservice))
            except UserError as error:
                hint_msg = re.search('.*(HINT|CONSEJO): (.*)', str(error))
                if hint_msg:
                    msg = hint_msg.groups()[-1] if hint_msg and len(hint_msg.groups()) > 1 \
                        else '\n'.join(re.search('.*' + webservice + ': (.*)\n\n', str(error)).groups())
                else:
                    msg = str(error)
                results.append(
                    _("* %(webservice)s: Connection failed. %(message)s", webservice=webservice, message=msg.strip())
                )
            except Exception as error:
                results.append(
                    _(
                        "* %(webservice)s: Connection failed. This is what we get: %(error)s",
                        webservice=webservice,
                        error=repr(error),
                    ),
                )

        raise UserError("\n".join(results))

    def random_demo_cert(self):
        self.company_id.set_demo_random_cert()

    def _inverse_l10n_ar_payment_foreign_currency(self):
        for record in self:
            self.env['ir.config_parameter'].sudo().set_param(
                f"l10n_ar_edi.{record.company_id.id}_foreign_currency_payment", record.l10n_ar_payment_foreign_currency)
