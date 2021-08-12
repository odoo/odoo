# -*- coding: utf-8 -*-

from odoo import fields, models, api,_

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    factura_cfdi = fields.Boolean('Factura CFDI')
    tipo_comprobante = fields.Selection(
        selection=[('I', 'Ingreso'), 
                   ('E', 'Egreso'),
                    ('T', 'Traslado'),],
        string=_('Tipo de comprobante'),
    )
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
                   ('99', '99 - Por definir'),],
        string=_('Forma de pago'),
    )
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
    estado_factura = fields.Selection(
        selection=[('factura_no_generada', 'Factura no generada'), ('factura_correcta', 'Factura correcta'), 
                   ('problemas_factura', 'Problemas con la factura'), ('factura_cancelada', 'Factura cancelada'), ],
        string=_('Estado de factura'),
        default='factura_no_generada',
        readonly=True
    )	
    numero_cetificado = fields.Char(string=_('Numero de certificado'))
#    cetificaso_sat = fields.Char(string=_('Certificado SAT'))
    folio_fiscal = fields.Char(string=_('Folio Fiscal'))
    fecha_certificacion = fields.Datetime(string=_('Fecha y Hora Certificación'))
#    cadena_origenal = fields.Char(string=_('Cadena Original del Complemento digital de SAT'))
    selo_digital_cdfi = fields.Char(string=_('Sello Digital del CDFI'))
    selo_sat = fields.Char(string=_('Sello del SAT'))
    moneda = fields.Char(string=_('Moneda'))
    tipocambio = fields.Char(string=_('Tipo de cambio'))
#    folio = fields.Char(string=_('Folio'))
#    version = fields.Char(string=_('Version'))   
#    invoice_datetime = fields.Char(string=_('11/12/17 12:34:12'))
    tipo_relacion = fields.Selection(
        selection=[('01', 'Nota de crédito de los documentos relacionados'), 
                   ('02', 'Nota de débito de los documentos relacionados'), 
                   ('03', 'Devolución de mercancía sobre facturas o traslados previos'),
                   ('04', 'Sustitución de los CFDI previos'), 
                   ('05', 'Traslados de mercancías facturados previamente'),
                   ('06', 'Factura generada por los traslados previos'), 
                   ('07', 'CFDI por aplicación de anticipo'),],
        string=_('Tipo relación'),
    )
    uuid_relacionado = fields.Char(string=_('CFDI Relacionado'))
    
    @api.multi
    def action_view_invoice(self):
        res = super(PurchaseOrder,self).action_view_invoice()
        if res:
            if res.get('context')==None:
                res['context']={}
            res['context'].update({
                'default_factura_cfdi' : self.factura_cfdi,
                'default_tipo_comprobante' : self.tipo_comprobante,
                'default_forma_pago' : self.forma_pago,
                'default_methodo_pago' : self.methodo_pago,
                'default_uso_cfdi' : self.uso_cfdi,
                'default_estado_factura' : self.estado_factura,
                'default_numero_cetificado' : self.numero_cetificado,
                'default_folio_fiscal' : self.folio_fiscal,
                'default_fecha_certificacion' : self.fecha_certificacion,
                'default_selo_digital_cdfi' : self.selo_digital_cdfi,
                'default_selo_sat' : self.selo_sat,
                'default_moneda' : self.moneda,
                'default_tipocambio' : self.tipocambio,
                'default_tipo_relacion' : self.tipo_relacion,
                'default_uuid_relacionado' : self.uuid_relacionado 
                })
            
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:            			