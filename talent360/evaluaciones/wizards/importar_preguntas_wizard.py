import base64
import csv
from io import StringIO
from odoo import models, fields, api, exceptions, _

class ImportQuestionsWizard(models.TransientModel):
    _name = 'importar.preguntas.wizard'
    _description = 'Wizard to import questions from CSV'

    archivo = fields.Binary()

    
    nombre_archivo = fields.Char()

    required_fields = [
        "Pregunta",
        "Tipo",
        "Ponderacion",
        "Categoria",
    ]

    @api.constrains("nombre_archivo")
    def _validate_filename(self):
        if self.nombre_archivo and not self.nombre_archivo.lower().endswith(".csv"):
            raise exceptions.ValidationError(_("Solo se aceptan archivos CSV."))

    def import_questions(self):
        if not self.archivo:
            raise exceptions.ValidationError(_("Por favor, suba un archivo CSV."))

        try:
            contenido = base64.b64decode(self.archivo)
            archivo = StringIO(contenido.decode("utf-8"))
            csv_lector = csv.DictReader(archivo)

        except Exception as e:
            raise exceptions.ValidationError(
                f"Error al procesar el archivo: {str(e)}. Verifica que el archivo sea un CSV válido."
            )
        
        preguntas = []

        self._validate_columns(csv_lector.fieldnames)

        for i, fila in enumerate(csv_lector):
            if i >= 500:
                raise exceptions.ValidationError(
                    _("Error: No se pueden cargar más de 500 preguntas.")
                )
            
            self._validar_fila(fila)

            preguntas.append(
                {
                    "pregunta_texto": fila["Pregunta"],
                    "tipo": fila["Tipo"],
                    "ponderacion": fila["Ponderacion"],
                    "categoria": fila["Categoria"],
                }
            )

        preguntas_db = self.env["pregunta"].create(preguntas)
        evaluacion = self.env["evaluacion"].browse(self._context.get("active_id"))
        
        if evaluacion:
            evaluacion.write({'pregunta_ids': [(4, pregunta.id) for pregunta in preguntas_db]})
        else:
            raise exceptions.ValidationError(_("No se encontró la evaluación en el contexto."))
        
    
    def _validate_columns(self, columnas: list[str]):
        # Valida que las columnas del archivo CSV sean las correctas
        columnas_faltantes = []
        columnas_duplicadas = []

        for columna in self.required_fields:
            if columna not in columnas:
                columnas_faltantes.append(columna)

            if columnas.count(columna) > 1:
                columnas_duplicadas.append(columna)

        mensaje = ""

        if columnas_faltantes:
            mensaje += f"Las siguientes columnas son requeridas: {', '.join(columnas_faltantes)}\n"

        if columnas_duplicadas:
            mensaje += f"Las siguientes columnas están duplicadas: {', '.join(columnas_duplicadas)}\n"

        if mensaje:
            raise exceptions.ValidationError(mensaje)

    def _validar_fila(self, row: dict):
        campos = []
        for campo in self.required_fields:
            if not row.get(campo):
                campos.append(campo)

        if campos:
            raise exceptions.ValidationError(
                f"Los siguientes campos son requeridos: {', '.join(campos)}"
            )


    def descargar_template(self):
        # Define el contenido del archivo CSV de la plantilla
        ruta_archivo = (
            "talent360/evaluaciones/static/csv/plantilla_preguntas_clima.csv"
        )
        with open(ruta_archivo, "r") as archivo:
            datos = archivo.read()
            nombre_archivo = "plantilla_preguntas_clima.csv"

            attachment = self.env["ir.attachment"].search(
                [("name", "=", nombre_archivo), ("res_model", "=", self._name)], limit=1
            )

            if attachment:
                attachment.write({"datas": base64.b64encode(datos.encode("utf-8"))})
            else:
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": nombre_archivo,
                        "type": "binary",
                        "datas": base64.b64encode(datos.encode("utf-8")),
                        "res_model": nombre_archivo,
                        "res_id": self.id,
                    }
                )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{str(attachment.id)}?download=true",
            "target": "new",
        }
