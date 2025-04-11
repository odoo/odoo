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
    # ponemos default a los selectio porque al ser requeridos si no se comporta raro y parece que elige uno por defecto
    # pero que no esta seleccionado
    data_source = fields.Selection(
        [('data_source_cordoba', 'Web Service Córdoba')],
    )
    tax_template_domain = fields.Char(compute='_compute_tax_template_domain')
    default_tax_id = fields.Many2one('account.tax', required=True)
    tax_type = fields.Selection([('withholding', 'Withholding'), ('perception', 'Perception')], required=True, default='withholding')

    @api.constrains('fiscal_position_id', 'default_tax_id')
    def _check_tax_group_overlap(self):
        for record in self:
            domain = [
                ('id', '!=', record.id),
                ('fiscal_position_id', '=', record.fiscal_position_id.id),
                ('default_tax_id.tax_group_id', '=', record.default_tax_id.tax_group_id.id),
            ]
            conflicting_records = self.search(domain)
            if conflicting_records:
                raise ValidationError("No puede haber dos impuestos del mismo grupo para la misma posicion fiscal.")

    def _get_missing_taxes(self, partner, date):
        taxes = self.env['account.tax']
        for rec in self:
            if rec.data_source:
                taxes += rec._get_tax_from_ws(partner, date)
            else:
                taxes += rec.default_tax_id
        return taxes

    @api.depends('fiscal_position_id', 'tax_type')
    def _compute_tax_template_domain(self):
        for rec in self:
            rec.tax_template_domain = rec._get_tax_domain(filter_tax_group=False)

    def _get_tax_domain(self, filter_tax_group=True):
        self.ensure_one()
        domain = self.env['account.tax']._check_company_domain(self.fiscal_position_id.company_id)
        if filter_tax_group:
            domain += [('tax_group_id', '=', self.default_tax_id.tax_group_id.id)]
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
        aliquot, ref = getattr(self, '_get_%s_data' % self.data_source)(partner, date, to_date)
        # devolvemos None si es no inscripto
        if aliquot is None:
            tax = self.default_tax_id
        else:
            tax = self._ensure_tax(aliquot)
        # por mas que sea no inscripto creamos partner aliquot porque si no en cada
        # nueva linea o cambio se conecta a ws
        self.env['l10n_ar.partner.tax'].create({
            'partner_id': partner.id,
            'tax_id': tax.id,
            'from_date': from_date,
            'to_date': to_date,
            'ref': ref,
        })
        return tax

    def _get_data_source_cordoba_data(self, partner, date, to_date):
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
        ref = json_body.get("message")

        # Capturar Códigos de Error.
        # 3 => No Inscripto, 2 => No pasible, 1 => CUIT incorrecta, 0 => OK
        # casos como adhoc devuelven 1, no encuentra el cuit.
        # lo consideramos igual que no inscripto (no queremos que de raise)
        # estamos guardando igual en el partner info del mensaje (ref)
        if code in [3, 1]:
            aliquot = None
        elif code == 2:
            aliquot = 0.0
        else:
            dict_alic = json_body.get("sdtConsultaAlicuotas")
            aliquot = float(dict_alic.get("CRD_ALICUOTA_RET")) if self.tax_type == 'withholding' else float(dict_alic.get("CRD_ALICUOTA_PER"))
            # Verificamos si el par_cod no es para los recien inscriptos, que vienen con fecha "0000-00-00"
            if dict_alic.get("CRD_PAR_CODIGO") != 'NUE_INS':
                # Verificar que el comprobante tenga fecha dentro de la vigencia
                from_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_INICIO"))
                to_date_date = fields.Date.from_string(dict_alic.get("CRD_FECHA_FIN"))
                if not (from_date_date <= date <= to_date_date):
                    raise UserError(
                        'No se puede obtener automáticamente la alicuota para la '
                        'fecha %s. Por favor, ingrese la misma manualmente '
                        'en el partner.' % date)

        return aliquot, ref
