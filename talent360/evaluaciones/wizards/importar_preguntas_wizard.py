import base64
import csv
from io import StringIO
import os
from odoo import models, fields, api, exceptions, _

class ImportarPreguntasWizard(models.TransientModel):
    _name = "importar.preguntas.wizard"
    _description = "Asistente para importar preguntas desde CSV"

    archivo = fields.Binary()
    nombre_archivo = fields.Char()

    campos_requeridos = [
        "Pregunta",
        "Tipo",
        "Ponderacion",
        "Categoria",
        "Opciones"
    ]

    tipos_validos = ["multiple_choice", "open_question", "escala"]
    ponderaciones_validas = ["ascendente", "descendente"]
    categorias_validas = [
        "datos_generales",
        "reclutamiento_y_seleccion_de_personal",
        "formacion_y_capacitacion",
        "permanencia_y_ascenso",
        "corresponsabilidad_en_la_vida_laboral_familiar_y_personal",
        "clima_laboral_libre_de_violencia",
        "acoso_y_hostigamiento",
        "accesibilidad",
        "respeto_a_la_diversidad",
        "condiciones_generales_de_trabajo"
    ]

    @api.constrains("nombre_archivo")
    def _validar_nombre_archivo(self):
        if self.nombre_archivo and not self.nombre_archivo.lower().endswith(".csv"):
            raise exceptions.ValidationError(_("Solo se aceptan archivos CSV."))

    def importar_preguntas(self):
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

        self._validar_columnas(csv_lector.fieldnames)

        for i, fila in enumerate(csv_lector):
            if i >= 200:
                raise exceptions.ValidationError(
                    _("Error: No se pueden cargar más de 200 preguntas.")
                )

            self._validar_fila(fila)

            pregunta_data = {
                "pregunta_texto": fila["Pregunta"],
                "tipo": fila["Tipo"],
                "categoria": fila["Categoria"],
            }

            if fila["Tipo"] == "escala":
                pregunta_data["ponderacion"] = fila["Ponderacion"]

            pregunta = self.env["pregunta"].create(pregunta_data)

            if fila["Tipo"] == "multiple_choice":
                opciones = fila["Opciones"].split(",")
                for opcion_texto in opciones:
                    self.env["opcion"].create({
                        "pregunta_id": pregunta.id,
                        "opcion_texto": opcion_texto.strip(),
                        "valor": opciones.index(opcion_texto) + 1
                    })

            preguntas.append(pregunta)

        evaluacion = self.env["evaluacion"].browse(self._context.get("active_id"))

        if evaluacion:
            evaluacion.write({"pregunta_ids": [(4, pregunta.id) for pregunta in preguntas]})
        else:
            raise exceptions.ValidationError(_("No se encontró la evaluación en el contexto."))

    def _validar_columnas(self, columnas: list[str]):
        columnas_faltantes = []
        columnas_duplicadas = []

        for columna in self.campos_requeridos:
            if columna not in columnas:
                columnas_faltantes.append(columna)

            if columnas.count(columna) > 1:
                columnas_duplicadas.append(columna)

        mensaje = ""

        if columnas_faltantes:
            mensaje += f"Las siguientes columnas son requeridas: {', '.join(columnas_faltantes)}\n"

        if columnas_duplicadas:
            mensaje += f"Las siguientes columnas están duplicadas: {',' .join(columnas_duplicadas)}\n"

        if mensaje:
            raise exceptions.ValidationError(mensaje)

    def _validar_fila(self, fila: dict):
        if not fila.get("Pregunta") or not fila["Pregunta"].strip():
            raise exceptions.ValidationError(_("El campo 'Pregunta' es requerido y no puede estar vacío o solo contener espacios en blanco."))
        if not fila.get("Tipo"):
            raise exceptions.ValidationError(_("El campo 'Tipo' es requerido."))
        if not fila.get("Categoria"):
            raise exceptions.ValidationError(_("El campo 'Categoria' es requerido."))

        if fila["Tipo"] not in self.tipos_validos:
            raise exceptions.ValidationError(
                f"El tipo de pregunta '{fila['Tipo']}' no es válido. Los tipos permitidos son: {', '.join(self.tipos_validos)}."
            )

        if fila["Categoria"] not in self.categorias_validas:
            raise exceptions.ValidationError(
                f"La categoría '{fila['Categoria']}' no es válida. Las categorías permitidas son: {', '.join(self.categorias_validas)}."
            )

        if fila["Tipo"] == "escala":
            if not fila.get("Ponderacion"):
                raise exceptions.ValidationError(
                    "La ponderación es requerida para preguntas de tipo 'escala'."
                )
            if fila["Ponderacion"] not in self.ponderaciones_validas:
                raise exceptions.ValidationError(
                    f"La ponderación '{fila['Ponderacion']}' no es válida. Las ponderaciones permitidas son: {', '.join(self.ponderaciones_validas)}."
                )
        else:
            if fila.get("Ponderacion"):
                raise exceptions.ValidationError(
                    f"No se permite la ponderación para preguntas de tipo '{fila['Tipo']}'."
                )

    
        if fila["Tipo"] == "multiple_choice":
            if not fila.get("Opciones"):
                raise exceptions.ValidationError(
                    "Las opciones son requeridas para preguntas de tipo 'multiple_choice'."
                )
            opciones = [opcion.strip() for opcion in fila["Opciones"].split(",")]

            if len(opciones) != len(set(opciones)):
                raise exceptions.ValidationError(
                    "Las opciones para preguntas de tipo 'multiple_choice' no deben contener duplicados."
                )
            

            if len(opciones) > 10 or len(opciones) < 2:
                raise exceptions.ValidationError(
                    "Las opciones para preguntas de tipo 'multiple_choice' tienen que ser más que 2 y menos que 10."
                )

      
            for opcion in opciones:
                if not opcion.strip():
                    raise exceptions.ValidationError(
                        "Las opciones para preguntas de tipo 'multiple_choice' no pueden estar vacías o contener solo espacios en blanco."
                    )
        else:
    
            if fila.get("Opciones"):
                raise exceptions.ValidationError(
                    f"No se permiten opciones para preguntas de tipo '{fila['Tipo']}'."
                )

    def descargar_template(self):

        ruta_archivo = os.path.join(os.path.dirname(__file__), "../static/csv/plantilla_preguntas_clima.csv")

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
                        "res_model": self._name,
                        "res_id": self.id,
                    }
                )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{str(attachment.id)}?download=true",
            "target": "new",
        }
