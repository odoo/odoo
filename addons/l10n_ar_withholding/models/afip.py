from odoo import models, fields


class AfipEarningsTableScale(models.Model):
    _name = 'afip.earnings_table.scale'
    _description = 'afip.earnings_table.scale'
    _rec_name = 'importe_desde'

    importe_desde = fields.Float(
        'Mas de $',
    )
    importe_hasta = fields.Float(
        'A $',
    )
    importe_fijo = fields.Float(
        '$',
    )
    porcentaje = fields.Float(
        'Más el %'
    )
    importe_excedente = fields.Float(
        'S/ Exced. de $'
    )
    codigo_de_regimen = fields.Char(
        'Codigo de Regimen'
    )


class AfipTablagananciasAlicuotasymontos(models.Model):
    _name = 'afip.tabla_ganancias.alicuotasymontos'
    _description = 'afip.tabla_ganancias.alicuotasymontos'
    _rec_name = 'codigo_de_regimen'

    codigo_de_regimen = fields.Char(
        'Codigo de regimen',
        size=6,
        required=True,
        help='Codigo de regimen de inscripcion en impuesto a las ganancias.'
    )
    anexo_referencia = fields.Char(
        required=True,
    )
    concepto_referencia = fields.Text(
        required=True,
    )
    porcentaje_inscripto = fields.Float(
        '% Inscripto',
        help='Elija -1 si se debe calcular s/escala'
    )
    porcentaje_no_inscripto = fields.Float(
        '% No Inscripto'
    )
    montos_no_sujetos_a_retencion = fields.Float(
    )
