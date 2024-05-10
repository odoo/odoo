import base64
import csv
from datetime import datetime
from io import StringIO

from odoo import fields, models, api, exceptions


class AsignarUsuariosExternosWizard(models.TransientModel):
    _name = "asignar.usuario.externo.wizard"

    file = fields.Binary("Archivo")

    filename = fields.Char()

    @api.constrains("filename")
    def _check_filename(self):
        if self.filename and not self.filename.lower().endswith(".csv"):
            raise exceptions.ValidationError("Solo se aceptan archivos CSV.")

    def procesar_csv(self):

        evaluacion = self.env["evaluacion"].browse(self._context.get("active_id"))

        if not evaluacion:
            raise exceptions.ValidationError("No se encontró la evaluación en el contexto.")

        # Procesa el archivo CSV y crea los usuarios externos
        try:
            file_content = base64.b64decode(self.file)
            file = StringIO(file_content.decode("utf-8"))
            csv_reader = csv.DictReader(file)

        except Exception as e:
            raise exceptions.ValidationError(
                f"Error al procesar el archivo: {str(e)}. Verifica que el archivo sea un CSV válido."
            )
        
        users = []

        self.validar_columnas(csv_reader.fieldnames)

        for row in csv_reader:
            try:
                fecha_ingreso = datetime.strptime(row["Fecha de ingreso"], "%d/%m/%Y").date()
                fecha_nacimiento = datetime.strptime(row["Fecha de nacimiento"], "%d/%m/%Y").date()
            except ValueError:
                raise exceptions.ValidationError(
                    "El formato de las fechas debe ser dd/mm/yyyy. Verifica las fechas de nacimiento e ingreso."
                )

            users.append(
                {
                    "nombre": row["Nombre Completo"],
                    "email": row["Correo"],
                    "puesto": row["Puesto"],
                    "nivel_jerarquico": row["Nivel Jerárquico"],
                    "direccion": row["Dirección"],
                    "gerencia": row["Gerencia"],
                    "jefatura": row["Jefatura"],
                    "genero": row["Género"],
                    "fecha_ingreso": row["Fecha de ingreso"],
                    "fecha_nacimiento": row["Fecha de nacimiento"],
                    "region": row["Ubicación/Región"],
                }
            )

        for user in users:
            usuario_externo = self.env["usuario.externo"].create(
                {
                    "nombre": user["nombre"],
                    "email": user["email"],
                    "puesto": user["puesto"],
                    "nivel_jerarquico": user["nivel_jerarquico"],
                    "direccion": user["direccion"],
                    "gerencia": user["gerencia"],
                    "jefatura": user["jefatura"],
                    "genero": user["genero"],
                    "fecha_ingreso": fecha_ingreso,
                    "fecha_nacimiento": fecha_nacimiento,
                    "region": user["region"],
                }
            )

            evaluacion.write({"usuario_externo_ids": [(4, usuario_externo.id)]})
            
    def validar_columnas(self, columnas: list[str]):
        # Valida que las columnas del archivo CSV sean las correctas
        required_columns = [
            "Nombre Completo",
            "Correo",
            "Puesto",
            "Nivel Jerárquico",
            "Dirección",
            "Gerencia",
            "Jefatura",
            "Género",
            "Fecha de ingreso",
            "Fecha de nacimiento",
            "Ubicación/Región",
        ]

        columnas_faltantes = []
        columnas_duplicadas = []

        for column in required_columns:
            if column not in columnas:
                columnas_faltantes.append(column)

                if columnas.count(column) > 1:
                    columnas_duplicadas.append(column)

        mensaje = ""

        if columnas_faltantes:
            mensaje += f"Las siguientes columnas son requeridas: {', '.join(columnas_faltantes)}\n"

        if columnas_duplicadas:
            mensaje += f"Las siguientes columnas están duplicadas: {', '.join(columnas_duplicadas)}\n"

        if mensaje:
            raise exceptions.ValidationError(mensaje)

    def descargar_template_usuarios(self):
        # Descarga el archivo /evaluaciones/static/csv/template_usuarios_externos.csv
        file_path = "talent360/evaluaciones/static/csv/template_usuarios_externos.csv"
        with open(file_path, "r") as file:
            file_data = file.read()
            file_name = "template_usuarios_externos.csv"

            attachment = self.env["ir.attachment"].search(
                [("name", "=", file_name), ("res_model", "=", self._name)], limit=1
            )

            if not attachment:
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": file_name,
                        "type": "binary",
                        "datas": base64.b64encode(file_data.encode("utf-8")),
                        "res_model": file_name,
                        "res_id": self.id,
                    }
                )

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{str(attachment.id)}?download=true",
            "target": "new",
        }
