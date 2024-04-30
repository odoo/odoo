from odoo import api, models, fields

class ReporteResumen(models.Model):

    _name = 'evaluacion'
    _description = 'Reporte Resumen'
    _inherit = 'evaluacion'

    conteo_asignados = fields.Char(string='Asignados', compute='_compute_conteo_asignados', store="False")

    @api.depends('usuario_ids')
    def _compute_conteo_asignados(self):
        for record in self:
            conteo = len(record.usuario_ids)
            if conteo == 0:
                record.conteo_asignados = 'Sin asignados'
            elif conteo == 1:
                record.conteo_asignados = '1 asignado'
            else:
                record.conteo_asignados = f"{conteo} asignados"