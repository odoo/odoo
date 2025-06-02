# mi_website_ext/wizards/publication_view_wizard.py
from odoo import models, fields, api


class PublicationViewWizard(models.TransientModel):
    _name = "publication.view.wizard"
    _description = "Asistente para ver seguimiento de lecturas"

    # Campo para que RRHH seleccione qué publicación quiere analizar
    publication_id = fields.Many2one(
        "website.publication",
        string="Publicación",
        required=True,
        domain="[('publication_type', 'in', ['announce', 'policy', 'activity', 'news', 'blog'])]",
    )

    view_logs = fields.Many2many(
        comodel_name="publication.view.log",
        string="Registros de Vistas",
        compute="_compute_view_logs",
        readonly=True
    )

    # Dos campos para mostrar los resultados
    read_by_user_ids = fields.Many2many(
        "res.users",
        "publication_wizard_users_read_rel",  # Nombre de la tabla de relación
        "wizard_id",  # Nombre de la columna para este wizard
        "user_id",  # Nombre de la columna para el usuario
        string="Leído Por",
        readonly=True,
    )
    unread_by_user_ids = fields.Many2many(
        "res.users",
        "publication_wizard_users_unread_rel",  # Nombre de tabla DIFERENTE
        "wizard_id",
        "user_id",
        string="Pendiente de Leer",
        readonly=True,
    )

    @api.onchange("publication_id")
    def _onchange_publication_id(self):
        """
        Cuando se selecciona una publicación, calcula las dos listas de usuarios.
        """
        self.read_by_user_ids = False
        self.unread_by_user_ids = False

        if self.publication_id:
            # 1. Obtenemos todos los usuarios activos del sistema
            all_users = self.env["res.users"].search(
                [("share", "=", False), ("active", "=", True)]
            )

            # 2. Obtenemos los registros de lectura para ESTA publicación
            read_logs = self.env["publication.view.log"].search(
                [
                    ("res_model", "=", "website.publication"),
                    ("res_id", "=", self.publication_id.id),
                ]
            )
            read_user_ids = read_logs.mapped("user_id")

            # 3. Calculamos las dos listas
            self.read_by_user_ids = read_user_ids
            self.unread_by_user_ids = all_users - read_user_ids
