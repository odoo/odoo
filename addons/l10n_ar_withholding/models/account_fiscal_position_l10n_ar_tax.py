from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import requests
import json
import re
import logging
_logger = logging.getLogger(__name__)


class AccountFiscalPositionL10nArTax(models.Model):
    _name = "account.fiscal.position.l10n_ar_tax"
    _description = "account.fiscal.position.l10n_ar_tax"

    fiscal_position_id = fields.Many2one('account.fiscal.position', required=True, ondelete='cascade')
    data_source = fields.Selection(
        [('data_source_cordoba', 'Web Service Córdoba')],
    )
    tax_template_domain = fields.Char(compute='_compute_tax_template_domain')
    default_tax_id = fields.Many2one('account.tax', required=True)
    # we set a default for the selection fields because being required, it behaves oddly and seems to choose a default one
    # but it is not actually selected
    tax_type = fields.Selection([('withholding', 'Withholding'), ('perception', 'Perception')], required=True, default='withholding')

    @api.constrains('fiscal_position_id', 'default_tax_id')
    def _check_tax_group_overlap(self):
        """Ensures that there are no overlapping argentinean tax groups for the same fiscal position.
        This constraint checks that no two records have the same fiscal position and
        belong to the same tax group. If such a conflict is found, a ValidationError
        is raised."""
        for record in self:
            domain = [
                ('id', '!=', record.id),
                ('fiscal_position_id', '=', record.fiscal_position_id.id),
                ('default_tax_id.tax_group_id', '=', record.default_tax_id.tax_group_id.id),
            ]
            conflicting_records = self.search(domain)
            if conflicting_records:
                raise ValidationError(_("There cannot be two taxes from the same group for the same tax position."))

    def _get_missing_taxes(self, partner, date):
        """Retrieve the missing taxes for the given partner and date.
        This method determines the taxes that are missing for a specific partner
        and date. It checks whether the `data_source` attribute is set for each
        record. If `data_source` is present, it fetches the taxes from a web
        service using the `_get_tax_from_ws` method. Otherwise, it uses the
        default tax specified in `default_tax_id`."""
        taxes = self.env['account.tax']
        for rec in self:
            if rec.data_source:
                taxes += rec._get_tax_from_ws(partner, date)
            else:
                taxes += rec.default_tax_id
        return taxes

    @api.depends('fiscal_position_id', 'tax_type')
    def _compute_tax_template_domain(self):
        """Compute the tax template domain based on the fiscal position and tax type.
        This method is triggered by changes in the 'fiscal_position_id' or 'tax_type' fields.
        It updates the 'tax_template_domain' field for each record by calling the
        '_get_tax_domain' method with 'filter_tax_group' set to False."""
        for rec in self:
            rec.tax_template_domain = rec._get_tax_domain(filter_tax_group=False)

    def _get_tax_domain(self, filter_tax_group=True):
        """Generate the domain for filtering taxes based on the fiscal position, tax type,
        and optionally the tax group."""
        self.ensure_one()
        domain = self.env['account.tax']._check_company_domain(self.fiscal_position_id.company_id)
        if filter_tax_group:
            domain += [('tax_group_id', '=', self.default_tax_id.tax_group_id.id)]
        if self.tax_type == 'perception':
            domain += [('type_tax_use', '=', 'sale')]
        elif self.tax_type == 'withholding':
            # for now, the 3 web services use iibb_untaxed, that's why it's hardcoded
            domain += [('l10n_ar_withholding_payment_type', '=', 'supplier')]
        return domain

    def _ensure_tax(self, rate):
        """
        Ensures the existence of a tax with the specified rate. If a tax with the given rate
        does not exist or is inactive, it creates or reactivates the tax.
        Returns:
            recordset: The `account.tax` record corresponding to the tax with the specified rate.

        Behavior:
            - Searches for an existing tax with the specified rate in the `account.tax` model.
            - If the tax is found but inactive, it reactivates the tax.
            - If no tax is found, it duplicates the `default_tax_id` record, updating its rate,
              sequence, and name to match the specified rate.
        """
        self.ensure_one()
        domain = self._get_tax_domain()
        tax = self.env['account.tax'].with_context(active_test=False).search(domain + [('amount', '=', rate)], limit=1)
        if not tax.active:
            tax.active = True
        if not tax:
            # Usamos re.sub para reemplazar el patrón con el nuevo número seguido de '%'
            name = re.sub(r'\b\d+(\.\d+)?\s*%', f'{rate}%', self.default_tax_id.name)

            tax = self.default_tax_id.copy(default={
                # dejamos sequencia mas baja para que siempre el que se duplica sea el que esta arriba
                'sequence': 10,
                'amount': rate,
                'active': True,
                'name': name,
            })
        return tax

    def _get_tax_from_ws(self, partner, date):
        """Retrieve tax information from a web service based on the partner and date.

        This method fetches tax data for a given partner and date range using a
        specified data source. If the partner is not registered, a default tax
        is returned. The method also ensures that partner tax data is stored
        to avoid repeated web service calls.

        Returns:
            account.tax: The tax object retrieved or the default tax if not registered.

        Raises:
            ValueError: If the specified data source is invalid."""
        self.ensure_one()
        from_date = date + relativedelta(day=1)
        to_date = from_date + relativedelta(days=-1, months=+1)
        get_data_source_methods = {
            'data_source_cordoba': self._get_data_source_cordoba_data,
        }
        if self.data_source not in get_data_source_methods:
            raise ValueError(_("Invalid data source: %(data_source)s", data_source=self.data_source))
        aliquot, ref = get_data_source_methods[self.data_source](partner, date, to_date)
        # return None if it is no inscripto
        if aliquot is None:
            tax = self.default_tax_id
        else:
            tax = self._ensure_tax(aliquot)
        # Even if the partner is no inscripto, we create a partner aliquot record
        # because otherwise, it connects to the web service for every new line or change.
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': partner.id,
            'tax_id': tax.id,
            'from_date': from_date,
            'to_date': to_date,
            'ref': ref,
        })
        return tax

    def _get_cordoba_response(self, partner):
        """ Fetch withholding tax rates from the Rentas Córdoba API.
        :param partner: The partner object containing VAT information.
        :type partner: res.partner
        :return: Response object from the API request.
        :rtype: requests.Response"""
        _logger.info(_('Getting withholding data from rentascordoba.gob.ar'))

        # Set request parameters
        payload = {'body': partner.vat}
        headers = {'content-type': 'application/json'}

        # Make request
        url = "https://app.rentascordoba.gob.ar/rentas/rest/svcGetAlicuotas"
        if not url.startswith("https://app.rentascordoba.gob.ar"):
            raise UserError(_("Invalid URL: %(url)s", url=url))
        with requests.Session() as session:
            rta = session.post(url, data=json.dumps(payload), headers=headers, timeout=5)
        return rta

    def _get_data_source_cordoba_data(self, partner, date, to_date):
        """Retrieve tax rates from the Cordoba tax authority API.

        :param partner: The partner for which the data is being retrieved.
        :param date: The date of the invoice or payment.
        :param to_date: The default end date for the validity of the tax rate.
        :return: A tuple containing the tax rate (aliquot) and a reference message.
        :raises UserError: If the API response indicates an error or if the tax rate
                           is not valid for the given date."""
        rta = self._get_cordoba_response(partner)
        json_body = rta.json()

        if rta.status_code != 200:
            raise UserError('Error al contactar app.rentascordoba.gob.ar '
                            'El servidor respondió: \n\n%s' % json_body)

        code = json_body.get("errorCod")
        ref = json_body.get("message")

        # Capture Error Codes.
        # 3 => No Inscripto, 2 => No pasible, 1 => CUIT incorrecta, 0 => OK
        # return 1 if the CUIT is not found.
        # We treat it the same as no inscripto (we don't want it to raise an error).
        # We are still saving the message info (ref) in the partner.
        if code in [3, 1]:
            aliquot = None
        elif code == 2:
            aliquot = 0.0
        else:
            dict_alic = json_body.get("sdtConsultaAlicuotas")
            aliquot = float(dict_alic.get("CRD_ALICUOTA_RET")) if self.tax_type == 'withholding' else float(dict_alic.get("CRD_ALICUOTA_PER"))
            # We check if the par_cod is not for newly registered entities, which come with the date "0000-00-00"
            if dict_alic.get("CRD_PAR_CODIGO") != 'NUE_INS':
                # Verify that the document date falls within the validity period
                from_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_INICIO"))
                to_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_FIN"))
                if not (from_date_date <= date <= to_date_date):
                    raise UserError(_(
                        'The tax rate cannot be automatically retrieved for the '
                        'date %(date)s. Please enter it manually '
                        'in the partner.', date=date))
        return aliquot, ref
