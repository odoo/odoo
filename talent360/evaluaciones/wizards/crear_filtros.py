from odoo import fields, models, api, exceptions, _


class FiltroSeleccion(models.TransientModel):
    """
    Modelo para manejar las selecciones de filtros en el wizard.

    Este modelo se utiliza para manejar las selecciones de filtros en el wizard de creación de filtros.

    :param texto: texto de la selección
    :param categoria: categoría de la selección, usado para filtrar en UI
    :param filtro_original_id: id del filtro original, usado para filtrar en UI
    :param filtro_id: id del filtro al que pertenece la selección
    """

    _name = "filtro.seleccion.wizard"
    _rec_name = "texto"

    texto = fields.Char()
    categoria = fields.Char()
    filtro_original_id = fields.Integer()
    filtro_id = fields.Many2one("filtro.wizard", string="Filtro")


class Filtro(models.TransientModel):
    """
    Modelo para manejar los filtros en el wizard.

    Este modelo se utiliza para manejar los filtros en el wizard de creación de filtros.

    :param categoria: categoría del filtro
    :param categoria_interna: categoría interna del filtro, se usa para acceder al valor del dato demografico al filtrar
    :param filtro_seleccion_ids: selecciones del filtro
    :param crear_filtros_wizard_id: id del wizard al que pertenece el filtro
    """

    _name = "filtro.wizard"
    _rec_name = "categoria"

    categoria = fields.Char("Filtro")
    categoria_interna = fields.Char()

    filtro_seleccion_ids = fields.One2many(
        "filtro.seleccion.wizard", "filtro_id", string="Valores"
    )

    crear_filtros_wizard_id = fields.Many2one("crear.filtros.wizard")


class CrearFiltrosWizard(models.TransientModel):
    """
    Modelo para manejar el wizard de creación de filtros.

    Este modelo se utiliza para manejar el wizard de creación de filtros para el reporte de evaluaciones.

    :param filtros_ids: filtros del wizard
    """

    _name = "crear.filtros.wizard"

    filtros_ids = fields.One2many(
        "filtro.wizard", "crear_filtros_wizard_id", string="Filtros"
    )

    def generar_reporte(self):
        """
        Método para generar el reporte de evaluación.

        Este método se encarga de generar el reporte de evaluación con los filtros seleccionados por el usuario.

        :return: acción para abrir el reporte en una nueva pestaña
        """

        evaluacion_id = self.env.context.get("actual_evaluacion_id")
        evaluacion = self.env["evaluacion"].browse(evaluacion_id)
        query_params = self.crear_filtros_query_params()

        return {
            "type": "ir.actions.act_url",
            "url": f"/evaluacion/reporte/{evaluacion.id}?{query_params}",
            "target": "new",
        }

    def crear_filtros_query_params(self):
        """
        Método para crear los query params de los filtros.

        Este método se encarga de crear los query params de los filtros seleccionados por el usuario.

        :return: query params de los filtros
        """

        filtros = []
        for filtro in self.filtros_ids:
            selecciones = filtro.filtro_seleccion_ids.mapped("texto")
            if not selecciones:
                continue

            selecciones = [f'"{seleccion}"' for seleccion in selecciones]
            filtro_str = ",".join(selecciones)
            filtros.append(f'"{filtro.categoria}":{"{"}"valores":[{filtro_str}],"categoria_interna":"{filtro.categoria_interna}"{"}"}')

        return "filtros={" + ",".join(filtros) + "}"
