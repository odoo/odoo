from odoo import models, fields, api
from datetime import timedelta


class WebsitePublication(models.Model):
    _name = "website.publication"
    _description = "Publicaciones del Sitio Web (Anuncios, Noticias, etc.)"
    _inherit = ["mail.thread", "mail.activity.mixin", "image.mixin"]
    _order = "publish_date desc, create_date desc"

    publication_type = fields.Selection(
        [
            ("announce", "Anuncio"),
            ("activity", "Actividad del Mes"),
            ("blog", "Blog"),
            ("news", "Noticia"),
            ("phrase", "Frase del Día"),
            ("special_event", "Evento Especial"),
            ("winner", "Ganador del Mes"),
            ("policy", "Política o Reglamento"),
        ],
        string="Tipo de Publicación",
        required=True,
        default="announce",
        index=True,
    )
    name = fields.Char(
        string="Título / Nombre del Ganador", required=True, translate=True
    )
    subtitle = fields.Char(
        string="Subtítulo",
        translate=True,
        help="Subtítulo para Actividades, Blogs o Noticias.",
    )

    # Usaremos un campo HTML para el contenido principal. El editor de Odoo permite añadir imágenes.
    content_html = fields.Html(
        string="Contenido / Párrafo Principal",
        translate=True,
        sanitize_attributes=False,
        help="Cuerpo principal de la publicación. Puedes insertar imágenes adicionales aquí.",
    )

    # Campos específicos para la "Frase del Día"
    author_name = fields.Char(string="Autor de la Frase")
    author_description = fields.Char(
        string="Descripción del Autor", help="Ej: Físico y matemático"
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado Festejado",
        help="Selecciona al empleado si esta publicación es sobre un cumpleaños o aniversario.",
    )

    # Campo para el estado
    is_published = fields.Boolean(
        string="Publicado en Sitio Web", default=True, index=True
    )
    publish_date = fields.Date(string="Fecha de Publicación", default=fields.Date.today)
    user_id = fields.Many2one(
        "res.users", string="Autor (Empleado)", default=lambda self: self.env.user
    )
    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company
    )

    # Campo para la URL en el frontend
    website_url = fields.Char(
        string="URL del Sitio Web",
        compute="_compute_website_url",
        help="URL de la página de detalle.",
    )
    winner_score = fields.Integer(string="Puntaje Obtenido")

    # Campos para la integración con el calendario
    activity_datetime = fields.Datetime(string="Fecha y Hora de la Actividad")
    calendar_event_id = fields.Many2one(
        "calendar.event", string="Evento de Calendario", readonly=True, copy=False
    )

    attachment_url = fields.Char(
        string="URL del Adjunto",
        compute="_compute_attachment_url",
        help="URL de descarga para el primer PDF adjunto.",
    )

    def _compute_attachment_url(self):
        for pub in self:
            # Buscamos el primer adjunto que sea un PDF para esta publicación
            attachment = self.env["ir.attachment"].search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", pub.id),
                    (
                        "mimetype",
                        "=",
                        "application/pdf",
                    ),  # Filtramos para que sea un PDF
                ],
                limit=1,
                order="create_date desc",
            )

            if attachment:
                # Construimos la URL de descarga correcta
                pub.attachment_url = f"/web/content/{attachment.id}"
            else:
                pub.attachment_url = False

    def _get_url_base_for_publication(self):
        """Método auxiliar para obtener la URL base según el tipo."""
        self.ensure_one()
        # Mapeo de tipos a las URLs base de tus plantillas de detalle
        url_map = {
            "announce": "/announce",
            "activity": "/activity",
            "blog": "/blog",  # Asumiendo que es una lista y el detalle es /blog/slug-o-id
            "news": "/news_detail",
            "birthday": "/birthday_single",
            "anniversary": "/anniversary",
            "phrase": False,
            "special_event": False,  # Los eventos especiales tampoco, se muestran en el sidebar
        }
        return url_map.get(self.publication_type, False)

    def _compute_website_url(self):
        for publication in self:
            base_url = publication._get_url_base_for_publication()
            if base_url and publication.id:
                # URL amigable simple con ID. Más adelante se puede mejorar con un "slug".
                publication.website_url = f"{base_url}/{publication.id}"
            else:
                publication.website_url = False

    # Al final de la clase WebsitePublication

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered(lambda r: r.publication_type == "activity"):
            record._synchronize_calendar_event()
        return records

    def write(self, vals):
        res = super().write(vals)
        for record in self.filtered(lambda r: r.publication_type == "activity"):
            record._synchronize_calendar_event()
        return res

    def _synchronize_calendar_event(self):
        self.ensure_one()
        if not self.activity_datetime:
            # Si no hay fecha de actividad, no hacemos nada (o borramos el evento existente)
            if self.calendar_event_id:
                self.calendar_event_id.unlink()
            return

        event_vals = {
            "name": self.name,
            "start": self.activity_datetime,
            "stop": self.activity_datetime
            + timedelta(hours=1),  # Asumimos 1 hora de duración
            "description": self.subtitle,
            # Puedes añadir más campos, como 'location', 'partner_ids', etc.
        }

        if self.calendar_event_id:
            # Si ya existe un evento, lo actualizamos
            self.calendar_event_id.write(event_vals)
        else:
            # Si no existe, lo creamos y guardamos su ID
            event = self.env["calendar.event"].create(event_vals)
            self.write(
                {"calendar_event_id": event.id}
            )  # Usamos write para no causar recursión

    @api.onchange("employee_id", "publication_type")
    def _onchange_set_name_for_winner(self):
        """
        Cuando el tipo es 'Ganador' y se selecciona un empleado,
        se genera un título automáticamente.
        """
        if self.publication_type == "winner" and self.employee_id:
            self.name = f"Ganador: {self.employee_id.name}"
