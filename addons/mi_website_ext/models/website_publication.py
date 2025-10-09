from odoo import models, fields, api
from datetime import timedelta
import logging

from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class WebsitePublication(models.Model):
    _name = "website.publication"
    _description = "Publicaciones del Sitio Web (Anuncios, Noticias, etc.)"
    _inherit = ["mail.thread", "mail.activity.mixin", "image.mixin"]
    _order = "publish_date desc, create_date desc"
    policy_pdf = fields.Binary("PDF de la Política")
    policy_pdf_filename = fields.Char("Nombre del archivo PDF")

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

    content_html = fields.Html(
        string="Contenido / Párrafo Principal",
        translate=True,
        sanitize_attributes=False,
        help="Cuerpo principal de la publicación. Puedes insertar imágenes adicionales aquí.",
    )

    author_name = fields.Char(string="Autor de la Frase")
    author_description = fields.Char(
        string="Descripción del Autor", help="Ej: Físico y matemático"
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado Festejado",
        help="Selecciona al empleado si esta publicación es sobre un cumpleaños o aniversario.",
    )

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

    website_url = fields.Char(
        string="URL del Sitio Web",
        compute="_compute_website_url",
        help="URL de la página de detalle.",
    )
    winner_score = fields.Integer(string="Puntaje Obtenido")

    winner_month = fields.Selection([
        ('Enero', 'Enero'),
        ('Febrero', 'Febrero'),
        ('Marzo', 'Marzo'),
        ('Abril', 'Abril'),
        ('Mayo', 'Mayo'),
        ('Junio', 'Junio'),
        ('Julio', 'Julio'),
        ('Agosto', 'Agosto'),
        ('Septiembre', 'Septiembre'),
        ('Octubre', 'Octubre'),
        ('Noviembre', 'Noviembre'),
        ('Diciembre', 'Diciembre'),
    ], string="Mes del Ganador")

    activity_datetime = fields.Datetime(string="Fecha y Hora de la Actividad")
    calendar_event_id = fields.Many2one(
        "calendar.event", string="Evento de Calendario", readonly=True, copy=False
    )

    policy_pdf = fields.Binary("PDF de la Política")
    policy_pdf_filename = fields.Char("Nombre del archivo PDF")

    attachment_url = fields.Char(
        string="URL del Adjunto",
        compute="_compute_attachment_url",
        help="URL de descarga para el primer PDF adjunto.",
    )


    def _compute_attachment_url(self):
        for pub in self:
       
            if pub.policy_pdf:
                pub.attachment_url = f"/web/content/{pub._name}/{pub.id}/policy_pdf"
            else:
       
                attachment = self.env["ir.attachment"].search(
                    [
                        ("res_model", "=", self._name),
                        ("res_id", "=", pub.id),
                        ("mimetype", "=", "application/pdf"),
                    ],
                    limit=1,
                    order="create_date desc",
                )
                if attachment:
                    pub.attachment_url = f"/web/content/{attachment.id}"
                else:
                    pub.attachment_url = False

    def _get_url_base_for_publication(self):
        self.ensure_one()
       
        url_map = {
            "announce": "/announce",
            "activity": "/activity",
            "blog": "/blog",  
            "news": "/news_detail",
            "birthday": "/birthday_single",
            "anniversary": "/anniversary",
            "phrase": False,
            "special_event": False,  
        }
        return url_map.get(self.publication_type, False)

    def _compute_website_url(self):
        for publication in self:
            base_url = publication._get_url_base_for_publication()
            if base_url and publication.id:
                publication.website_url = f"{base_url}/{publication.id}"
            else:
                publication.website_url = False

    def open_view_wizard(self):
        self.ensure_one()

        if self.publication_type not in ['announce', 'policy', 'activity', 'news', 'blog']:
            raise UserError("Este tipo de publicación no admite seguimiento de lecturas.")
    
        return {
            'type': 'ir.actions.act_window',
            'name': 'Ver Seguimiento de Lectura',
            'res_model': 'publication.view.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('mi_website_ext.view_publication_view_wizard_form').id,
            'target': 'new',
            'context': {
                'default_publication_id': self.id,
            }
        }

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
            if self.calendar_event_id:
                self.calendar_event_id.unlink()
            return

        event_vals = {
            "name": self.name,
            "start": self.activity_datetime,
            "stop": self.activity_datetime
            + timedelta(hours=1),  
            "description": self.subtitle,
        }

        if self.calendar_event_id:
            self.calendar_event_id.write(event_vals)
        else:
            event = self.env["calendar.event"].create(event_vals)
            self.write(
                {"calendar_event_id": event.id}
            )  

    @api.onchange("employee_id", "publication_type")
    def _onchange_set_name_for_winner(self):
        if self.publication_type == "winner" and self.employee_id:
            self.name = f"Ganador: {self.employee_id.name}"



    @api.model
    def _publish_scheduled_posts(self):
        _logger.info("Ejecutando cron de publicación programada...")

        posts_to_publish = self.search([
            ('is_published', '=', False),
            ('publish_date', '<=', fields.Date.today())
        ])

        if posts_to_publish:
            posts_to_publish.write({'is_published': True})
            _logger.info(f"Se han publicado {len(posts_to_publish)} posts programados.")
        else:
            _logger.info("No se encontraron posts para publicar hoy.")

        return True     
