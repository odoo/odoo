from odoo import fields, models, api, exceptions, _

class RegistrarAvance(models.TransientModel):
    _name = "registrar.avance.wizard"
    _description = "Registrar Avance Wizard"

    fecha = fields.Date(string='Fecha', default=fields.Date.today())
    avance = fields.Integer(string='Avance', required=True)
    archivos = fields.Many2many(comodel_name='ir.attachment', string='Subir Archivo')
    nombres_archivos = fields.Char(string='Nombres de Archivos')
    comentarios = fields.Text(string='Comentarios')
            
    @api.constrains('avance')
    def _validar_avance(self):
        for registro in self:
            if registro.avance == 0:
                raise exceptions.ValidationError(_('Por favor registra el avance del objetivo'))
            elif registro.avance < 0:
                raise exceptions.ValidationError(_('El avance no puede ser negativo'))

    @api.constrains('archivos')
    def _validar_peso_archivo(self):
        maximo = 100 * 1024 * 1024
        for registro in self:
            for archivo in registro.archivos:
                if archivo.file_size > maximo:
                    raise exceptions.ValidationError(_('El archivo no debe ser mayor a 100 MB'))
    
    @api.constrains('archivos')
    def _validar_tipo_archivo(self):
        archivos_permitidos = ['csv', 'xlsx', 'txt', 'pdf', 'png', 'jpeg', 'jpg']
        for archivo in self.archivos:
            nombre, tipo_archivo = archivo.name.rsplit('.', 1)
            if tipo_archivo.lower() not in archivos_permitidos:
                    raise exceptions.ValidationError(_('Solo se pueden subir archivos con extensión pdf, xlsx, csv, txt, png, jpeg'))
                
    @api.constrains('comentarios')
    def _validar_comentarios(self):
        for registro in self:
            if registro.comentarios:
                palabras = len(registro.comentarios.split())
                if palabras > 200:
                    raise exceptions.ValidationError(_('Los comentarios no deben exceder las 200 palabras'))
    
    @api.constrains('archivos')
    def _validar_numero_archivos(self):
        for registro in self:
            if len(registro.archivos) > 10:
                raise exceptions.ValidationError(_('Solo se puede subir un máximo de 10 archivos'))

    
    def action_confirmar(self):
        avance = self.avance
        archivos = self.archivos
        comentarios = self.comentarios
        fecha = self.fecha
        
        objetivo_id = self.env.context.get("objetivo_id")
        usuario_objetivo = self.env["objetivo"].browse(objetivo_id)
        
        self.env["objetivo.avances"].create({
            "objetivo_id": usuario_objetivo.id,
            "fecha": fecha,
            "avance": avance,
            "comentarios": comentarios,
            "archivos": [(6, 0, archivos.ids)],
        })
        
        usuario_objetivo.sudo().write({"resultado": avance})
        