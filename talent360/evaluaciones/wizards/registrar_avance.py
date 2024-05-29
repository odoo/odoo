from odoo import fields, models, api, exceptions, _

class RegistrarAvance(models.TransientModel):
    """
    Modelo para registrar un avance de un objetivo de desempeño

    :param _name(str): Nombre del modelo en Odoo
    :param _description (str): Descripción del modelo en Odoo
    :param fecha (fields.Date): Fecha en la que se registra un avance
    :param avance (fields.Integer): Avance del objetivo
    :param archivos (fields.Many2Many): Archivos adjuntos al avance
    :param comentarios (fields.Text): Comentarios del avance
    """

    _name = "registrar.avance.wizard"
    _description = "Registrar Avance Wizard"

    fecha = fields.Date(default=fields.Date.today())
    avance = fields.Integer(
        required=True,
        help="Avance que consideras que has logrado en el objetivo."
    )

    archivos = fields.Many2many(
        required=True,
        comodel_name="ir.attachment",
        string="Subir Archivo",
        help="Evidencias que sustenten el porqué del avance registrado. Solo se permiten archivos con extensión pdf, xlsx, csv, txt, png, jpeg"
    )

    nombres_archivos = fields.Char(string="Nombres de Archivos")
    comentarios = fields.Text(
        required=True,
        help="Comentarios que sustentan el avance que se está registrando."
    )

    @api.constrains("avance")
    def _validar_avance(self):
        """
        Método para validar que el avance no sea negativo y que no sea 0

        Si el avance es 0 o negativo, se levanta una excepción
        """

        for registro in self:
            if registro.avance == 0:
                raise exceptions.ValidationError(_("Por favor registra el avance del objetivo"))
            
            elif registro.avance < 0:
                raise exceptions.ValidationError(_("El avance no puede ser menor a 0"))
            
    @api.constrains("archivos")
    def _validar_no_archivos(self):
        """
        Método para validar que se suban archivos

        Si no se suben archivos, se levanta una excepción
        """

        for registro in self:
            if not registro.archivos:
                raise exceptions.ValidationError(_("Por favor sube al menos un archivo"))

    @api.constrains("archivos")
    def _validar_peso_archivo(self):
        """
        Método para validar que el peso del archivo no supere los 100 MB

        Si el peso del archivo supera los 100 MB, se levanta una excepción
        """

        maximo = 100 * 1024 * 1024

        for registro in self:
            for archivo in registro.archivos:
                if archivo.file_size > maximo:
                    raise exceptions.ValidationError(_("El archivo no debe ser mayor a 100 MB"))
    
    @api.constrains("archivos")
    def _validar_tipo_archivo(self):
        """
        Método para validar que los archivos cargados sean de tipo pdf, xlsx, 
        csv, txt, png, jpeg

        Si un archivo no es del tipo permitido, se levanta una excepción
        """

        archivos_permitidos = ["csv", "xlsx", "txt", "pdf", "png", "jpeg", "jpg"]

        for archivo in self.archivos:
            if '.' not in archivo.name:
                raise exceptions.ValidationError(_("No se pueden subir archivos sin extensión"))
            nombre, tipo_archivo = archivo.name.rsplit('.', 1)
            if tipo_archivo.lower() not in archivos_permitidos:
                    raise exceptions.ValidationError(_("Solo se pueden subir archivos con extensión pdf, xlsx, csv, txt, png, jpeg"))
    
    @api.constrains("comentarios")
    def _validar_comentarios(self):
        """
        Método para validar que los comentarios no excedan las 200 palabras

        Si los comentarios exceden las 200 palabras, se levanta una excepción
        """

        for registro in self:
            if registro.comentarios:
                palabras = len(registro.comentarios.split())
                if palabras > 200:
                    raise exceptions.ValidationError(_("Los comentarios no deben exceder las 200 palabras"))
                if len(registro.comentarios) > 600:
                    raise exceptions.ValidationError(_("Los comentarios no deben exceder los 600 caracteres"))
    
    @api.constrains("archivos")
    def _validar_numero_archivos(self):
        """
        Método para validar que no se suban más de 10 archivos

        Si se suben más de 10 archivos, se levanta una excepción
        """

        for registro in self:
            if len(registro.archivos) > 10:
                raise exceptions.ValidationError(_("Solo se puede subir un máximo de 10 archivos"))

    @api.constrains("archivos") 
    def _validar_contenido_archivos(self):
        """
        Método para validar que los archivos no estén vacíos

        Si un archivo está vacío, se levanta una excepción
        """

        for registro in self:
            for archivo in registro.archivos:
                if archivo.type == 'url':
                    raise exceptions.ValidationError(_("No se pueden subir URL, solo archivos. Por favor descarga el archivo y sube el archivo en lugar de la URL"))
                if not archivo.datas:
                    raise exceptions.ValidationError(_("El archivo no debe estar vacío"))   

    def confirmar_action(self):
        """
        Método para registrar un avance en un objetivo de desempeño
        
        Se crea un registro en el modelo objetivo.avances con los datos del avance
        Se actualiza el campo resultado del objetivo con la suma del valor del avance
        """

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
        
        nuevo_resultado = usuario_objetivo.resultado + avance
        usuario_objetivo.sudo().write({"resultado": nuevo_resultado})
        