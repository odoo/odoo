# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from  . import amount_to_text_es_MX
import pytz
from .tzlocal import get_localzone
from odoo import tools
import logging
_logger = logging.getLogger(__name__)
#----------------------------------------------------------
# Incoterms
#----------------------------------------------------------
class SaleOrder(models.Model):
    _inherit = 'sale.order'
      
    forma_pago = fields.Selection(
        selection=[('01', '01 - Efectivo'), 
                   ('02', '02 - Cheque nominativo'), 
                   ('03', '03 - Transferencia electrónica de fondos'),
                   ('04', '04 - Tarjeta de Crédito'), 
                   ('05', '05 - Monedero electrónico'),
                   ('06', '06 - Dinero electrónico'), 
                   ('08', '08 - Vales de despensa'), 
                   ('12', '12 - Dación en pago'), 
                   ('13', '13 - Pago por subrogación'), 
                   ('14', '14 - Pago por consignación'), 
                   ('15', '15 - Condonación'), 
                   ('17', '17 - Compensación'), 
                   ('23', '23 - Novación'), 
                   ('24', '24 - Confusión'), 
                   ('25', '25 - Remisión de deuda'), 
                   ('26', '26 - Prescripción o caducidad'), 
                   ('27', '27 - A satisfacción del acreedor'), 
                   ('28', '28 - Tarjeta de débito'), 
                   ('29', '29 - Tarjeta de servicios'),
                   ('30', '30 - Aplicación de anticipos'),
                   ('31', '31 - Intermediario pagos'),
                   ('99', '99 - Por definir'),],
        string=_('Forma de pago'),
    )
    #num_cta_pago = fields.Char(string=_('Núm. Cta. Pago'))
    methodo_pago = fields.Selection(
        selection=[('PUE', _('Pago en una sola exhibición')),
                   ('PPD', _('Pago en parcialidades o diferido')),],
        string=_('Método de pago'), 
    )
    uso_cfdi = fields.Selection(
        selection=[('G01', _('Adquisición de mercancías')),
                   ('G02', _('Devoluciones, descuentos o bonificaciones')),
                   ('G03', _('Gastos en general')),
                   ('I01', _('Construcciones')),
                   ('I02', _('Mobiliario y equipo de oficina por inversiones')),
                   ('I03', _('Equipo de transporte')),
                   ('I04', _('Equipo de cómputo y accesorios')),
                   ('I05', _('Dados, troqueles, moldes, matrices y herramental')),
                   ('I06', _('Comunicacion telefónica')),
                   ('I07', _('Comunicación Satelital')),
                   ('I08', _('Otra maquinaria y equipo')),
                   ('D01', _('Honorarios médicos, dentales y gastos hospitalarios')),
                   ('D02', _('Gastos médicos por incapacidad o discapacidad')),
                   ('D03', _('Gastos funerales')),
                   ('D04', _('Donativos')),
                   ('D07', _('Primas por seguros de gastos médicos')),
                   ('D08', _('Gastos de transportación escolar obligatoria')),
                   ('D10', _('Pagos por servicios educativos (colegiaturas)')),
                   ('P01', _('Por definir')),],
        string=_('Uso CFDI (cliente)'),
    )
    fecha_corregida = fields.Datetime(string=_('Fecha Cotizacion'), compute='_get_fecha_corregida')

    @api.multi
    @api.onchange('partner_id')
    def _get_uso_cfdi(self):
        if self.partner_id:
            values = {
                'uso_cfdi': self.partner_id.uso_cfdi
                }
            self.update(values)

    @api.multi
    @api.onchange('payment_term_id')
    def _get_metodo_pago(self):
        if self.payment_term_id:
            if self.payment_term_id.methodo_pago == 'PPD':
                values = {
                 'methodo_pago': self.payment_term_id.methodo_pago,
                 'forma_pago': '99'
             }
            else:
                values = {
                 'methodo_pago': self.payment_term_id.methodo_pago,
                 'forma_pago': False
             }
        else:
            values = {
                'methodo_pago': False,
                'forma_pago': False
                }
        self.update(values)

    @api.depends('amount_total', 'currency_id')
    @api.one
    def _get_amount_to_text(self):
        self.amount_to_text = amount_to_text_es_MX.get_amount_to_text(self, self.amount_total, 'es_cheque', self.currency_id.name)
        
    @api.model
    def _get_amount_2_text(self, amount_total):
        return amount_to_text_es_MX.get_amount_to_text(self, amount_total, 'es_cheque', self.currency_id.name)
        
    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({'forma_pago': self.forma_pago,
                    'methodo_pago': self.methodo_pago,
                    'uso_cfdi': self.uso_cfdi,
                    'tipo_comprobante': 'I'
                    })
        return invoice_vals

    @api.multi
    def _get_fecha_corregida(self):
        if self.date_order:
           #corregir hora
           timezone = self._context.get('tz')
           if not timezone:
               timezone = self.env.user.partner_id.tz or 'America/Mexico_City'
           #timezone = tools.ustr(timezone).encode('utf-8')

           local = pytz.timezone(timezone)
           naive_from = self.date_order
           local_dt_from = naive_from.replace(tzinfo=pytz.UTC).astimezone(local)
           self.fecha_corregida = local_dt_from.strftime ("%Y-%m-%d %H:%M:%S")
           #_logger.info('fecha ... %s', self.fecha_corregida)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
