# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import re
import requests
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    # Campos movidos desde account.fiscal.position.l10n_ar_tax
    l10n_ar_data_source = fields.Selection(
        [('l10n_ar_data_source_cordoba', 'Web Service Córdoba')],
        string='(AR) Data Source',
    )
    l10n_ar_default_aliquot = fields.Float(digits=(16, 4), default=0.0, string='(AR) Default Aliquot')
    l10n_ar_withholding_or_perception = fields.Char(compute='_compute_l10n_ar_withholding_or_perception', string='(AR) Withholding or Perception')

    def _compute_l10n_ar_withholding_or_perception(self):
        """Return the tax type based on the tax group type."""
        for rec in self:
            if rec.l10n_ar_tribute_afip_code in ['06', '07', '08', '09']:
                rec.l10n_ar_withholding_or_perception = 'perception'
            elif not rec.l10n_ar_tribute_afip_code and not rec.l10n_ar_vat_afip_code:
                rec.l10n_ar_withholding_or_perception = 'withholding'
            else:
                rec.l10n_ar_withholding_or_perception = False

    def _get_missing_taxes(self, partner, date, company):
        """Retrieve the missing taxes for the given partner and date.
        This method determines the taxes that are missing for a specific partner
        and date. It checks whether the `l10n_ar_data_source` attribute is set for each
        record. If `l10n_ar_data_source` is present, it fetches the taxes from a web
        service using the `_get_tax_from_ws` method. Otherwise, it uses the
        first available tax in the tax group."""
        taxes = self.env['account.tax']
        for rec in self:
            if rec.l10n_ar_data_source:
                taxes += rec._get_tax_from_ws(partner, date, company)
            else:
                # Find the first tax in this tax group
                domain = company._check_company_domain(company)
                domain += [('tax_group_id', '=', rec.id)]
                available_tax = self.env['account.tax'].search(domain, limit=1)
                if not available_tax:
                    raise UserError(_(
                        'No tax found for tax group "%(group_name)s"". '
                        'Please configure at least one tax for this group.',
                        group_name=rec.name,
                    ))
                taxes += available_tax
        return taxes

    def _get_tax(self, aliquot=None):
        """Generate the domain for filtering taxes based on the tax group, tax type,
        and optionally the company."""
        self.ensure_one()
        domain = self.env['account.tax']._check_company_domain(self.company_id)
        domain += [('tax_group_id', '=', self.id)]
        if aliquot is not None:
            domain += [('amount', '=', aliquot)]
        return self.env['account.tax'].with_context(active_test=False).search(domain, limit=1)

    def _ensure_tax(self, rate, company):
        """
        Ensures the existence of a tax with the specified rate. If a tax with the given rate
        does not exist or is inactive, it creates or reactivates the tax.
        Returns:
            recordset: The `account.tax` record corresponding to the tax with the specified rate.

        Behavior:
            - Searches for an existing tax with the specified rate in the `account.tax` model.
            - If the tax is found but inactive, it reactivates the tax.
            - If no tax is found, it duplicates the first available tax in this group, updating its rate,
              sequence, and name to match the specified rate.
        """
        self.ensure_one()
        tax = self._get_tax(rate)
        if tax and not tax.active:
            tax.active = True
        if not tax:
            # Find a template tax to copy from
            template_tax = self._get_tax(rate)
            if not template_tax:
                raise UserError(_(
                    'No template tax found for tax group "%(group_name)s". '
                    'Please configure at least one tax for this group.',
                    group_name=self.name,
                ))

            # Use regex to replace the percentage in the name
            name = re.sub(r'\b\d+(\.\d+)?\s*%', f'{rate}%', template_tax.name)

            tax = template_tax.copy(default={
                # Keep lower sequence so the duplicated one is always on top
                'sequence': 10,
                'amount': rate,
                'active': True,
                'name': name,
            })
        return tax

    def _get_tax_from_ws(self, partner, date, company):
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
        get_l10n_ar_data_source_methods = {
            'l10n_ar_data_source_cordoba': self._get_l10n_ar_data_source_cordoba_data,
        }
        if self.l10n_ar_data_source not in get_l10n_ar_data_source_methods:
            raise ValueError(_("Invalid data source: %(l10n_ar_data_source)s", l10n_ar_data_source=self.l10n_ar_data_source))
        aliquot, ref = get_l10n_ar_data_source_methods[self.l10n_ar_data_source](partner, date, to_date)
        # return None if it is no inscripto
        if aliquot is None:
            # Get default tax from this group
            default_tax = self._get_tax(self.l10n_ar_default_aliquot)
            if not default_tax:
                raise UserError(_(
                    'No default tax found for tax group "%(group_name)s". '
                    'Please configure at least one tax for this group.',
                    group_name=self.name,
                ))
            tax = default_tax
        else:
            tax = self._ensure_tax(aliquot, company)
        # Even if the partner is not inscripto, we create a partner aliquot record
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
            return session.post(url, data=json.dumps(payload), headers=headers, timeout=5)

    def _get_l10n_ar_data_source_cordoba_data(self, partner, date, to_date):
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
            aliquot = float(dict_alic.get("CRD_ALICUOTA_RET")) if self.l10n_ar_withholding_or_perception == 'withholding' else float(dict_alic.get("CRD_ALICUOTA_PER"))
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
