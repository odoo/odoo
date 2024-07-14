# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.exceptions import UserError
import datetime
from odoo.tools import format_date


class ResCurrency(models.Model):

    _inherit = "res.currency"

    def l10n_ar_action_get_afip_ws_currency_rate(self):
        date, rate = self._l10n_ar_get_afip_ws_currency_rate()
        date = format_date(self.env, datetime.datetime.strptime(date, '%Y%m%d'), date_format='EEEE, dd MMMM YYYY')
        raise UserError(_('Last Business Day') + ': %s' % date + '\n' + _('Rate:') + ' %s' % rate)

    def _l10n_ar_get_afip_ws_currency_rate(self, afip_ws='wsfe'):
        """ Return the date and rate for a given currency
        This is only for the user so that he can quickly check the last rate on afip por a currency.
        This is really useful. There is a NTH for the future to integrate this with the automtaic currency rates """
        self.ensure_one()
        if not self.l10n_ar_afip_code:
            raise UserError(_('No AFIP code for currency %s. Please configure the AFIP code consulting information in AFIP page', self.name))
        if self.l10n_ar_afip_code == 'PES':
            raise UserError(_('No rate for ARS (is the base currency for AFIP)'))

        connection = self.env.company._l10n_ar_get_connection(afip_ws)
        client, auth = connection._get_client()
        if afip_ws == 'wsfe':
            response = client.service.FEParamGetCotizacion(auth, MonId=self.l10n_ar_afip_code)
            if response.Errors:
                raise UserError(_('The was an error obtaining the rate:\n\n * Code %s -  %s', response.Errors.Err[0].Code, response.Errors.Err[0].Msg))
            # Events None
            date = response.ResultGet.FchCotiz
            rate = response.ResultGet.MonCotiz
        elif afip_ws == 'wsfex':
            response = client.service.FEXGetPARAM_Ctz(auth, Mon_id=self.l10n_ar_afip_code)
            date = response.FEXResultGet.Mon_fecha
            rate = response.FEXResultGet.Mon_ctz
        else:
            raise UserError(_('Get AFIP currency rate not implemented for webservice %s', afip_ws))
        return date, rate
