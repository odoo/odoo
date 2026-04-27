from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.translate import LazyTranslate
from odoo.tools.xml_utils import find_xml_value
from odoo.addons.iap.tools import iap_tools

_lt = LazyTranslate(__name__)


class DanishReportCustomHandler(models.AbstractModel):
    _name = 'l10n_dk.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Danish Report Custom Handler'

    ERROR_MESSAGES = {
        '4801': _lt("RSU is not delegated by the legal entity (See Onboard Legal Entities: https://skat.dk/erhverv/moms/momsregnskab)."),
        '4802': _lt("The VAT period is not open."),
        '4803': _lt("The VAT period has not ended."),
        '4804': _lt("The VAT period is more than 3 years old."),
        '4810': _lt("The VAT statement draft has not been approved."),
        '4811': _lt("No receipt, the provisional VAT return has been rejected."),
        '4812': _lt("Receipt does not exist."),
        '4813': _lt("The VAT statement draft does not exist."),
        '4816': _lt("The value in the 'description' field does not exist. Should be 'Moms'."),
        '4817': _lt("The search start date is later than the search end date."),
        '8283': _lt("Search period cannot span more than 2 years."),
    }

    # Allows to translate the errors returned by IAP
    ERROR_MESSAGES_IAP = {
        'error_subscription': _lt("An error has occurred when trying to verify your subscription."),
        'dbuuid_not_exist': _lt("Your database uuid does not exist."),
        'not_enterprise': _lt("You do not have an Odoo enterprise subscription."),
        'not_prod_env': _lt("Your database is not used for a production environment."),
        'not_active_db': _lt("Your database is not yet activated."),
        'error_deprecated': _lt("Please upgrade the Danish Localization - RSU module.")
    }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['buttons'].append({'name': _('Send report'), 'sequence': 150, 'action': 'action_send_tax_report_rsu'})

    @api.model
    def action_send_tax_report_rsu(self, options):
        wizard = self.env['l10n_dk_rsu.tax.report.calendar.wizard'].create({
            'report_id': options['report_id'],
            'company_id': self.env.company.id,
        })
        return wizard._get_records_action(
            name=_('Tax Report RSU Calendar'),
            target='new',
        )

    @api.model
    def _create_envelope(self, body):
        params = {
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'body_xml': body,
        }
        endpoint = self.env['ir.config_parameter'].sudo().get_param('iap.l10n_dk_rsu_proxy_endpoint', 'https://l10n-dk-rsu.api.odoo.com')
        response = iap_tools.iap_jsonrpc(f'{endpoint}/api/l10n_dk_rsu/v1/create_header', params=params)

        if error_code := response.get('error'):
            raise UserError(self.ERROR_MESSAGES_IAP[error_code])
        return response

    def _error_code_handler(self, response):
        """
            This method will take the response given by the government and send the right error depending on the error
            code provided in the response.
        """
        if fault_message := find_xml_value('.//faultstring', response):
            raise UserError(_("Something went wrong: Service error - %s", fault_message))

        if error_codes := response.xpath('.//ns:FejlIdentifikator', namespaces={'ns': "http://rep.oio.dk/skat.dk/basis/kontekst/xml/schemas/2006/09/01/"}):
            raise UserError(_(
                "Something went wrong:\n%s",
                "\n".join(
                    self.ERROR_MESSAGES.get(error_code.text) or error_code.text for error_code in error_codes
                )
            ))
