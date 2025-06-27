import base64
from odoo import http, fields
from odoo.http import request
import logging
from dateutil.relativedelta import relativedelta
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class WebsiteCustom(http.Controller):
    @http.route("/galeria", type="http", auth="public", website=True)
    def render_gallery(self, **kwargs):
        # Buscamos todos los álbumes que estén publicados
        albums = request.env["website.gallery.album"].search(
            [("is_published", "=", True)]
        )

        values = {
            "albums": albums,
            "hide_sidebar": True,
        }
        return request.render("mi_website_ext.gallery_template", values)

    @http.route(
        ['/gallery/album/<model("website.gallery.album"):album>'],
        type="http",
        auth="public",
        website=True,
    )
    def render_gallery_album_detail(self, album, **kwargs):
        # Verificamos que el álbum esté publicado
        if not album.is_published:
            return request.not_found()

        values = {
            "album": album,
            "photos": album.photo_ids,  # Pasamos las fotos del álbum a la plantilla
            "main_object": album,
            "hide_sidebar": True,
        }
        return request.render("mi_website_ext.gallery_detail_template", values)

    @http.route("/blogs", type="http", auth="public", website=True)
    def render_blog(self, **kwargs):
        blog_posts = request.env["website.publication"].search(
            [
                ("publication_type", "=", "blog"),
                ("is_published", "=", True),
            ],
            order="publish_date desc",
        )
        values = {"blog_posts": blog_posts, "hide_sidebar": True}
        return request.render("mi_website_ext.blog_template", values)

    @http.route(
        ['/blog/<model("website.publication"):publication>'],
        type="http",
        auth="public",
        website=True,
    )
    def render_blog_detail(self, publication, **kwargs):
        if not publication.is_published or publication.publication_type != "blog":
            return request.not_found()
        has_read = (
            request.env["publication.view.log"]
            .sudo()
            .search_count(
                [
                    ("res_model", "=", "website.publication"),
                    ("res_id", "=", publication.id),
                    ("user_id", "=", request.env.user.id),
                ]
            )
            > 0
        )
        values = {
            "publication": publication,
            "main_object": publication,
            "hide_sidebar": True,
            "has_read": has_read,
        }
        # Asegúrate de tener una plantilla llamada 'blog_post_detail_template'
        return request.render("mi_website_ext.blog_post_detail_template", values)

    @http.route("/news", type="http", auth="public", website=True)
    def render_news(self, **kwargs):
        news_posts = request.env["website.publication"].search(
            [
                ("publication_type", "=", "news"),
                ("is_published", "=", True),
            ],
            order="publish_date desc",
        )
        values = {"news_posts": news_posts, "hide_sidebar": True}
        return request.render("mi_website_ext.news_template", values)

    @http.route(
        ['/news_detail/<model("website.publication"):publication>'],
        type="http",
        auth="public",
        website=True,
    )
    def render_news_detail(self, publication, **kwargs):
        if not publication.is_published or publication.publication_type != "news":
            return request.not_found()
        has_read = (
            request.env["publication.view.log"]
            .sudo()
            .search_count(
                [
                    ("res_model", "=", "website.publication"),
                    ("res_id", "=", publication.id),
                    ("user_id", "=", request.env.user.id),
                ]
            )
            > 0
        )

        values = {
            "publication": publication,
            "main_object": publication,
            "hide_sidebar": True,
            "has_read": has_read,
        }
        return request.render("mi_website_ext.news_detail_template", values)

    @http.route("/task", type="http", auth="public", website=True)
    def render_task(self, **kwargs):
        return request.render("mi_website_ext.task_template")

    @http.route("/policy", type="http", auth="user", website=True)
    def render_policy(self, **kwargs):
        # 1. Buscamos en el modelo 'website.publication' con el tipo 'policy'
        Publication = request.env['website.publication']
        policies = Publication.search([
            ('publication_type', '=', 'policy'),
            ('is_published', '=', True),
        ])

        # 2. Buscamos en 'publication.view.log' los registros de lectura para estas publicaciones
        read_logs = request.env['publication.view.log'].search([
            ('user_id', '=', request.env.user.id),
            ('res_model', '=', 'website.publication'), # El modelo de origen es 'website.publication'
            ('res_id', 'in', policies.ids)
        ])
        read_policy_ids = read_logs.mapped('res_id')

        # 3. Preparamos y pasamos los datos a la plantilla
        values = {
            'policies': policies,
            'read_policy_ids': read_policy_ids,
            'hide_sidebar': True,
        }
        return request.render("mi_website_ext.policy_template", values)

    @http.route(
        ['/birthday_single/<model("hr.employee"):employee>'],
        type="http",
        auth="public",
        website=True,
    )
    def render_birthday_single(self, employee, **kwargs):
        if not employee.user_id:
            pass

        values = {
            "employee": employee,
            "main_object": employee,
            "hide_sidebar": True,
        }
        return request.render("mi_website_ext.birthday_single_template", values)

    @http.route("/birthday_all", type="http", auth="public", website=True)
    def render_birthday_all(self, **kwargs):
        return request.render("mi_website_ext.birthday_all_template")

    @http.route(
        ['/announce/<model("website.publication"):publication>'],
        type="http",
        auth="public",
        website=True,
    )
    def render_announce(self, publication, **kwargs):
        if not publication.is_published or publication.publication_type != "announce":
            return request.not_found()
        has_read = (
            request.env["publication.view.log"]
            .sudo()
            .search_count(
                [
                    ("res_model", "=", "website.publication"),
                    ("res_id", "=", publication.id),
                    ("user_id", "=", request.env.user.id),
                ]
            )
            > 0
        )

        values = {
            "publication": publication,
            "main_object": publication,
            "hide_sidebar": True,
            "has_read": has_read,
        }
        return request.render("mi_website_ext.announce_template", values)

    @http.route(
        ['/activity/<model("website.publication"):publication>'],
        type="http",
        auth="public",
        website=True,
    )
    def render_activity_detail(self, publication, **kwargs):
        if not publication.is_published or publication.publication_type != "activity":
            return request.not_found()
        has_read = (
            request.env["publication.view.log"]
            .sudo()
            .search_count(
                [
                    ("res_model", "=", "website.publication"),
                    ("res_id", "=", publication.id),
                    ("user_id", "=", request.env.user.id),
                ]
            )
            > 0
        )

        values = {
            "publication": publication,
            "main_object": publication,
            "hide_sidebar": True,
            "has_read": has_read,
        }
        return request.render("mi_website_ext.activity_template", values)

    @http.route("/activity_all", type="http", auth="public", website=True)
    def render_activity_all(self, **kwargs):
        return request.render("mi_website_ext.activity_all_template")

    @http.route(
        ['/anniversary/<model("hr.employee"):employee>'],
        type="http",
        auth="public",
        website=True,
    )
    def render_anniversary(self, employee, **kwargs):
        values = {
            "employee": employee,
            "main_object": employee,
            "hide_sidebar": True,
        }
        return request.render("mi_website_ext.anniversary_single_template", values)

    @http.route("/anniversary_all", type="http", auth="public", website=True)
    def render_anniversary_all(self, **kwargs):
        return request.render("mi_website_ext.anniversary_all_template")

    @http.route("/intern_all", type="http", auth="public", website=True)
    def render_intern_all(self, **kwargs):
        return request.render("mi_website_ext.intern_all_template")

    @http.route("/program", type="http", auth="public", website=True)
    def render_program(self, **kwargs):
        return request.render("mi_website_ext.program")

    # This is for the comments
    @http.route(
        "/portal/add_comment", type="json", auth="user", methods=["POST"], website=True
    )
    def add_portal_comment(self, res_model, res_id, content, parent_id=None, **kwargs):
        if not content or not content.strip():
            return {"error": "El comentario no puede estar vacío."}

        # Validar que el modelo sea uno de los permitidos para comentar
        if res_model not in ["website.publication", "hr.employee"]:
            return {"error": "Tipo de registro no válido para comentar."}

        try:
            vals = {
                "res_model": res_model,
                "res_id": int(res_id),
                "content": content,
                "author_id": request.env.user.partner_id.id,
            }
            if parent_id:
                vals["parent_id"] = int(parent_id)

            new_comment = request.env["publication.comment"].sudo().create(vals)

            # Recargar la página es la forma más simple de ver el nuevo comentario
            # En el futuro podemos hacerlo 100% dinámico con una plantilla QWeb de JS
            return {"success": True}
        except Exception as e:
            _logger.error(f"Error al crear comentario: {e}")
            return {"error": "No se pudo guardar el comentario."}

    @http.route(
        "/comment/toggle_like", type="json", auth="user", methods=["POST"], website=True
    )
    def toggle_comment_like(self, comment_id, **kwargs):
        Like = request.env["publication.comment.like"].sudo()
        existing_like = Like.search(
            [
                ("comment_id", "=", int(comment_id)),
                ("partner_id", "=", request.env.user.partner_id.id),
            ]
        )

        if existing_like:
            existing_like.unlink()
            liked = False
        else:
            Like.create(
                {
                    "comment_id": int(comment_id),
                    "partner_id": request.env.user.partner_id.id,
                }
            )
            liked = True

        comment = request.env["publication.comment"].browse(int(comment_id))
        return {"success": True, "liked": liked, "like_count": comment.like_count}

    @http.route("/get_calendar_activities", type="json", auth="public")
    def get_calendar_activities(self):
        # Buscamos eventos de los próximos 3 meses, por ejemplo
        today = fields.Date.today()
        limit_date = today + relativedelta(months=3)

        events = request.env["calendar.event"].search(
            [
                ("start", ">=", today),
                ("start", "<=", limit_date),
                # Puedes añadir un filtro para solo mostrar eventos públicos si quieres
            ]
        )

        # Formateamos los eventos para que FullCalendar los entienda
        event_list = []
        for event in events:
            event_list.append(
                {
                    "title": event.name,
                    "start": event.start.isoformat(),
                    "end": event.stop.isoformat() if event.stop else None,
                }
            )
        return event_list

    # En mi_website_ext/controllers/main.py
    # (Tus otras importaciones y rutas se quedan igual)

    # En mi_website_ext/controllers/main.py
    # (Tus otras importaciones y rutas se quedan igual)

    @http.route("/notify/absence", type="json", auth="user", methods=["POST"], website=True)
    def notify_absence(self, **kwargs):
        _logger.warning("✅ Se llamó correctamente a /notify/absence desde: %s", request.env.user.name)

        user = request.env.user
        employee = user.employee_id

        if not employee:
            return {
                "error": "Tu usuario no está vinculado a un empleado."
            }

        try:
            Leave = request.env["hr.leave"].sudo()
            today = fields.Date.context_today(self)

            leave_type = request.env['hr.leave.type'].sudo().browse(2).exists()
            if not leave_type:
                leave_type = request.env['hr.leave.type'].sudo().search([
                    ('name', '=', 'Ausencias por enfermedad')
                ], limit=1)

            if not leave_type or not leave_type.exists():
                return {"error": "No se encontró el tipo de ausencia por ID=2."}

            # Crear solicitud de ausencia
            Leave.create({
                "name": f"Ausencia por enfermedad - notificada por {employee.name}",
                "employee_id": employee.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": today,
                "request_date_to": today,
                "number_of_days": 1,
            })

            # Notificar en canal de Discuss
            channel_name = "rrhh-notificaciones-ausencia"
            channel = request.env["discuss.channel"].sudo().search([
                ("name", "=", channel_name)
            ], limit=1)

            if not channel:
                channel = request.env["discuss.channel"].sudo().create({
                    "name": channel_name,
                    "channel_type": "channel",
                    "public": "groups",
                    "group_ids": [(6, 0, [request.env.ref('base.group_hr_user').id])],
                })

            message_body = (
                f"<p>El colaborador <strong>{employee.name}</strong> ha notificado una ausencia por enfermedad para hoy.</p>"
            )

            channel.message_post(
                body=message_body,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

            return {
                "success": True,
                "message": "Notificación y solicitud de ausencia creadas correctamente.",
            }

        except Exception as e:
            import traceback
            _logger.error("Error completo:\n%s", traceback.format_exc())
            return {
                "Este feature estara habilitado proximamente."
            }

    @http.route("/get_popup_announcements", type="json", auth="user", website=True)
    def get_popup_announcements(self, **kwargs):
        announcements = request.env["website.publication"].search(
            [
                ("publication_type", "=", "announce"),
                ("is_published", "=", True),
            ],
            order="publish_date desc",
        )

        if not announcements:
            return []

        # Obtenemos los registros de lectura para estas publicaciones y el usuario actual
        read_logs = request.env["publication.view.log"].search(
            [
                ("user_id", "=", request.env.user.id),
                ("res_model", "=", "website.publication"),
                ("res_id", "in", announcements.ids),
            ]
        )
        read_announcement_ids = read_logs.mapped("res_id")

        # Construimos la lista de resultados, añadiendo si ya fue leído
        results = []
        for ann in announcements:
            results.append(
                {
                    "id": ann.id,
                    "name": ann.name,
                    "website_url": ann.website_url or f"/announcements/{ann.id}",
                    "is_read": ann.id
                    in read_announcement_ids,  # <-- Clave para el bloqueo
                }
            )
        return results

    @http.route(
        "/portal/mark_as_read", type="json", auth="user", methods=["POST"], website=True
    )
    def mark_as_read(self, res_model, res_id, **kwargs):
        # Validamos que el modelo sea uno de los que permitimos registrar
        allowed_models = [
            "website.publication"
        ]  # En el futuro puedes añadir más, como 'website.gallery.album'
        if res_model not in allowed_models:
            return {"error": "Tipo de contenido no válido."}

        try:
            # Verificamos si ya existe un registro para no duplicarlo
            existing_log = (
                request.env["publication.view.log"]
                .sudo()
                .search(
                    [
                        ("res_model", "=", res_model),
                        ("res_id", "=", int(res_id)),
                        ("user_id", "=", request.env.user.id),
                    ]
                )
            )
            if not existing_log:
                request.env["publication.view.log"].sudo().create(
                    {
                        "res_model": res_model,
                        "res_id": int(res_id),
                        "user_id": request.env.user.id,
                    }
                )
            return {"success": True}
        except Exception as e:
            _logger.error(f"Error al marcar como leído: {e}")
            return {"error": "No se pudo registrar la acción."}

    @http.route("/portal/sidebar/announcements", type="json", auth="user", website=True)
    def get_sidebar_announcements_html(self):
        recent_announcements = request.env["website.publication"].search(
            [
                ("publication_type", "=", "announce"),
                ("is_published", "=", True),
            ],
            order="publish_date desc",
        )

        read_logs = request.env["publication.view.log"].sudo().search(
            [
                ("user_id", "=", request.env.user.id),
                ("res_model", "=", "website.publication"),
                ("res_id", "in", recent_announcements.ids),
            ]
        )
        read_announcement_ids = read_logs.mapped("res_id")

        html = request.env["ir.ui.view"]._render_template(
            "mi_website_ext.sidebar_fragment_announcements",
            {
                "recent_announcements": recent_announcements,
                "read_announcement_ids": read_announcement_ids,
            },
        )
        return {"html": html}

    @http.route('/my/profile', type='http', auth='user', website=True)
    def my_custom_profile(self, **kwargs):
        values = {
            'user': request.env.user,
            'hide_sidebar': True, # Esta línea es crucial
        }
        return request.render("mi_website_ext.portal_my_profile", values)

    # ===== RUTA PARA ACTUALIZAR EL AVATAR (esta se queda igual) =====
    @http.route('/my/account/update_avatar', type='http', auth='user', methods=['POST'], website=True)
    def update_avatar(self, avatar, **post):
        user = request.env.user
        if avatar:
            user.write({
                'image_1920': base64.b64encode(avatar.read())
            })
        return request.redirect('/my/profile')