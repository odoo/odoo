from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from dateutil.relativedelta import relativedelta
import requests
import json
import re
import logging
_logger = logging.getLogger(__name__)



class AccountFiscalPositionL10nArTax(models.Model):
    _name = "account.fiscal.position.l10n_ar_tax"
    _description = "account.fiscal.position.l10n_ar_tax"

    company_id = fields.Many2one('res.company', ondelete='cascade')
    fiscal_position_id = fields.Many2one('account.fiscal.position', ondelete='cascade')
    # ponemos default a los selectio porque al ser requeridos si no se comporta raro y parece que elige uno por defecto
    # pero que no esta seleccionado
    webservice = fields.Selection(
        [('agip', 'AGIP (Regimen General)'), ('arba', 'ARBA'), ('rentas_cordoba', 'Rentas Cordoba')],
    )
    tax_group_id = fields.Many2one('account.tax.group', required=True)
    default_tax_id = fields.Many2one('account.tax', required=True)
    tax_type = fields.Selection([('withholding', 'Withholding'), ('perception', 'Perception')], compute='_compute_tax_type')

    def _compute_tax_type(self):
        for rec in self:
            rec.tax_type = 'withholding' if rec.company_id else 'perception'

    @api.constrains('fiscal_position_id', 'default_tax_id')
    def _check_tax_group_overlap(self):
        for record in self:
            domain = [
                ('id', '!=', record.id),
                ('fiscal_position_id', '=', record.fiscal_position_id.id),
                ('default_tax_id.tax_group_id', '=', record.default_tax_id.tax_group_id.id),
            ]
            if self.tax_type == 'withholding':
                # TODO esto lo deberiamos borrar al ir a odoo 19 y solo usar los tax groups
                # por ahora, para no renegar con scripts de migra que requieran crear tax groups para cada jurisdiccion y
                # ademas luego tener que ajustar a lo que hagamos en 19, usamos la jursdiccion como elemento de agrupacion
                # solo para retenciones
                domain += [('default_tax_id.l10n_ar_state_id', '=', self.default_tax_id.l10n_ar_state_id.id)]
            conflicting_records = self.search(domain)
            if conflicting_records:
                raise ValidationError("No puede haber dos impuestos del mismo grupo para la misma posicion fiscal.")

    def _get_missing_taxes(self, partner, date):
        taxes = self.env['account.tax']
        for rec in self:
            if rec.webservice:
                taxes += rec._get_tax_from_ws(partner, date)
            else:
                taxes += rec.default_tax_id
        return taxes

    def _get_tax_domain(self, filter_tax_group=True):
        self.ensure_one()
        domain = self.env['account.tax']._check_company_domain(self.fiscal_position_id.company_id)
        if filter_tax_group:
            domain += [('tax_group_id', '=', self.default_tax_id.tax_group_id.id)]
            if self.tax_type == 'withholding':
                # TODO esto lo deberiamos borrar al ir a odoo 19 y solo usar los tax groups
                # por ahora, para no renegar con scripts de migra que requieran crear tax groups para cada jurisdiccion y
                # ademas luego tener que ajustar a lo que hagamos en 19, usamos la jursdiccion como elemento de agrupacion
                # solo para retenciones
                domain += [('l10n_ar_state_id', '=', self.default_tax_id.l10n_ar_state_id.id)]
        if self.tax_type == 'perception':
            domain += [('type_tax_use', '=', 'sale')]
        elif self.tax_type == 'withholding':
            # por ahora los 3 ws usan iibb_untaxed por eso esta hardcodeado
            domain += [('l10n_ar_withholding_payment_type', '=', 'supplier')]
            # domain += [WTH Tax = iibb untaxed, (Arg with type = supplier), (type = none)]
        return domain

    def _ensure_tax(self, rate):
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
        self.ensure_one()
        from_date = date + relativedelta(day=1)
        to_date = from_date + relativedelta(days=-1, months=+1)
        aliquot, ref = getattr(self, '_get_%s_data' % self.webservice)(partner, date, to_date)
        # devolvemos None si es no inscripto
        if aliquot is None:
            tax = self.default_tax_id
        else:
            tax = self._ensure_tax(aliquot)
            self.env['l10n_ar.partner.tax'].create({
                'partner_id': partner.id,
                'tax_id': tax.id,
                'from_date': from_date,
                'to_date': to_date,
                'ref': ref,
            })
        return tax

    def _get_agip_data(self, partner, date, to_date):
        # si es base en data demo devolvemos una alicuota demo para que no falle la demo data
        if self.env.ref('base.user_demo', raise_if_not_found=False):
            return (
                2.5 if self.tax_type == 'withholding' else 3.0,
                'VALOR DUMMY | dummy'
            )
        raise UserError(_(
            'Falta configuración de credenciales de ADHOC para consulta de '
            'Alícuotas de AGIP'))

    def _get_arba_data(self, partner, date, to_date):
        self.ensure_one()

        cuit = partner.ensure_vat()
        _logger.info('Getting ARBA data for cuit %s from date %s to date %s' % (date, to_date, cuit))
        ws = self.fiscal_position_id.company_id.arba_connect()
        ws.ConsultarContribuyentes(
            date.strftime('%Y%m%d'),
            to_date.strftime('%Y%m%d'),
            cuit)

        error = False
        msg = False
        if ws.Excepcion:
            error = True
            msg = str((ws.Traceback, ws.Excepcion))
            _logger.error('Padron ARBA: Excepcion %s' % msg)

        # ' Hubo error general de ARBA?
        if ws.CodigoError:
            if ws.CodigoError == '11':
                # we still create the record so we don need to check it again
                # on same period
                _logger.info('CUIT %s not present on padron ARBA' % cuit)
            elif ws.CodigoError == '6':
                error = True
                msg = "%s\n Error %s: %s" % (ws.MensajeError, ws.TipoError, ws.CodigoError)
                _logger.error('Padron ARBA: %s' % msg)
            else:
                error = True
                msg = (_('Padron ARBA: %s - %s (%s)') % (ws.MensajeError, ws.TipoError, ws.CodigoError))
                _logger.error('Padron ARBA: %s' % msg)

        if error:
            action = self.env.ref('l10n_ar_tax.act_company_jurisdiction_padron')
            raise RedirectWarning(_(
                "Hubo un error al consultar el Padron ARBA. "
                "Para solucionarlo puede seguir los siguientes pasos, los cuales explicamos con más detalle en este video:\n %s\n\n"
                "Tiene las siguientes opciones:\n  1) Intentar nuevamente más tarde\n"
                "  2) Cargar la alícuota manualmente en el partner en cuestión\n"
                "  3) Subir el archivo del padrón utilizando el Asistente de carga de padrones.\n\n"
                "Error obtenido:\n%s\n\n") % ('https://docs.google.com/document/d/1Tb_0SGKexakuXMn_0in3Z5zLwoaVOgZhYwhQ7DiFjFw/edit', msg),
                action.id, _('Ir a Carga de Padrones'))

        # no ponemos esto, si no viene alicuota es porque es cero entonces
        # if not ws.AlicuotaRetencion or not ws.AlicuotaPercepcion:
        #     raise UserError('No pudimos obtener la AlicuotaRetencion')

        # si no hay numero de comprobante entonces es porque no
        # figura en el padron, aplicamos alicuota no inscripto
        if ws.NumeroComprobante:
            return (
                    ws.AlicuotaRetencion if self.tax_type == 'withholding' else ws.AlicuotaPercepcion,
                    '%s | %s | %s' % (ws.NumeroComprobante, ws.CodigoHash, ws.GrupoRetencion if self.tax_type == 'withholding' else ws.GrupoPercepcion)
                )
        else:
            return None, ws.CodigoHash

    def _get_rentas_cordoba_data(self, partner, date, to_date):
        """ Obtener alícuotas desde app.rentascordoba.gob.ar
        :param partner: El partner sobre el cual trabajamos
        :param date: La fecha del comprobante
        :param from_date: Fecha de inicio de validez de alícuota por defecto
        :param to_date: Fecha de fin de validez de alícuota por defecto
        Devuelve diccionario de datos
        """
        _logger.info('Getting withholding data from rentascordoba.gob.ar')

        # Establecer parámetros de solicitud
        url = "https://app.rentascordoba.gob.ar/rentas/rest/svcGetAlicuotas"
        payload = {'body': partner.vat}
        headers = {'content-type': 'application/json'}

        # Realizar solicitud
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        json_body = r.json()

        if r.status_code != 200:
            raise UserError('Error al contactar rentascordoba.gob.ar. '
                            'El servidor respondió: \n\n%s' % json_body)

        code = json_body.get("errorCod")

        # Capturar Códigos de Error.
        # 3 => No Inscripto, 2 => No pasible, 1 => CUIT incorrecta, 0 => OK
        if code == 3:
            aliquot = None
        elif code == 2:
            aliquot = 0.0
        elif code != 0:
            raise UserError(json_body.get("message"))
        else:
            dict_alic = json_body.get("sdtConsultaAlicuotas")
            aliquot = float(dict_alic.get("CRD_ALICUOTA_RET")) if self.tax_type == 'withholding' else float(dict_alic.get("CRD_ALICUOTA_PER"))
            # Verificamos si el par_cod no es para los recien inscriptos, que vienen con fecha "0000-00-00"
            if dict_alic.get("CRD_PAR_CODIGO") != 'NUE_INS':
                # Verificar que el comprobante tenga fecha dentro de la vigencia
                from_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_INICIO"))
                to_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_FIN"))
                if not (from_date_date <= date_date <= to_date_date):
                    raise UserError(
                        'No se puede obtener automáticamente la alicuota para la '
                        'fecha %s. Por favor, ingrese la misma manualmente '
                        'en el partner.' % date)
        return aliquot, False
