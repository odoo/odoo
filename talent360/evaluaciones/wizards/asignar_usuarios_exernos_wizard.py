import base64
import csv
from datetime import datetime
from io import StringIO

from odoo import fields, models, api, exceptions, _
import os


class AsignarUsuariosExternosWizard(models.TransientModel):
    _name = "asignar.usuario.externo.wizard"

    archivo = fields.Binary()

    nombre_archivo = fields.Char()

    campos_obligatorios = [
        "Nombre Completo",
        "Correo",
        "Puesto",
        "Nivel Jerarquico",
        "Direccion",
        "Gerencia",
        "Jefatura",
        "Genero",
        "Fecha de ingreso",
        "Fecha de nacimiento",
        "Ubicacion/Region",
    ]

    @api.constrains("nombre_archivo")
    def _validar_nombre_archivo(self):
        if self.nombre_archivo and not self.nombre_archivo.lower().endswith(".csv"):
            raise exceptions.ValidationError(_("Solo se aceptan archivos CSV."))

    def procesar_csv(self):

        evaluacion = self.env["evaluacion"].browse(self._context.get("active_id"))

        if not evaluacion:
            raise exceptions.ValidationError(
                _("No se encontró la evaluación en el contexto.")
            )

        # Procesa el archivo CSV y crea los usuarios externos
        try:
            contenidos = base64.b64decode(self.archivo)
            archivo = StringIO(contenidos.decode("utf-8"))
            csv_lector = csv.DictReader(archivo)

        except Exception as e:
            raise exceptions.ValidationError(
                f"Error al procesar el archivo: {str(e)}. Verifica que el archivo sea un CSV válido."
            )

        usuarios = []

        self.validar_columnas(csv_lector.fieldnames)

        for i, fila in enumerate(csv_lector):
            if i >= 50000:
                raise exceptions.ValidationError(
                    _("Error: No se pueden cargar más de 50,000 usuarios.")
                )
            try:
                fecha_ingreso = datetime.strptime(
                    fila["Fecha de ingreso"], "%d/%m/%Y"
                ).date()
                fecha_nacimiento = datetime.strptime(
                    fila["Fecha de nacimiento"], "%d/%m/%Y"
                ).date()
            except ValueError:
                raise exceptions.ValidationError(
                    _(
                        "El formato de las fechas debe ser dd/mm/yyyy. Verifica las fechas de nacimiento e ingreso."
                    )
                )

            self.validar_fila(fila)

            usuarios.append(
                {
                    "nombre": fila["Nombre Completo"],
                    "email": fila["Correo"],
                    "puesto": fila["Puesto"],
                    "nivel_jerarquico": fila["Nivel Jerarquico"],
                    "direccion": fila["Direccion"],
                    "gerencia": fila["Gerencia"],
                    "jefatura": fila["Jefatura"],
                    "genero": fila["Genero"],
                    "fecha_ingreso": fecha_ingreso,
                    "fecha_nacimiento": fecha_nacimiento,
                    "region": fila["Ubicacion/Region"],
                }
            )

        usuarios_db = self.env["usuario.externo"].create(usuarios)

        usuario_ids = [(4, usuario.id) for usuario in usuarios_db]
        evaluacion.write({"usuario_externo_ids": usuario_ids})

    def validar_columnas(self, columnas: list[str]):
        # Valida que las columnas del archivo CSV sean las correctas

        columnas_faltantes = []
        columnas_duplicadas = []

        for columna in self.campos_obligatorios:
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

    def validar_fila(self, row: dict):
        campos = []
        for campo in self.campos_obligatorios:
            if not row.get(campo):
                campos.append(campo)

        if campos:
            raise exceptions.ValidationError(
                f"Los siguientes campos son requeridos: {', '.join(campos)}"
            )

    def descargar_template_usuarios(self):
        # Descarga el archivo /evaluaciones/static/csv/template_usuarios_externos.csv
        current_path = os.path.dirname(os.path.abspath(__file__))
        ruta_archivo = os.path.join(
            current_path, "../static/csv/template_usuarios_externos.csv"
        )
        with open(ruta_archivo, "r") as archivo:
            datos = archivo.read()
            nombre_archivo = "template_usuarios_externos.csv"

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
