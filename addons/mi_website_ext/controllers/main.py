import base64
from odoo import http, fields
from odoo.http import request, Controller
import logging
from dateutil.relativedelta import relativedelta
from odoo.addons.portal.controllers.portal import CustomerPortal
from werkzeug.utils import redirect

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
        employee_sudo = employee.sudo()
        if not employee_sudo.user_id:
            pass

        values = {
            "employee": employee_sudo,
            "main_object": employee_sudo,
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
        years_in_company = 0
        employee_sudo = employee.sudo()
        if employee_sudo and employee_sudo.contract_ids:
            first_contract = employee_sudo.contract_ids.sorted(lambda c: c.date_start or fields.Date.today())[0]
            if first_contract.date_start:
                hire_year = first_contract.date_start.year
                current_year = fields.Date.today().year
                if fields.Date.today().month == first_contract.date_start.month:
                    years_in_company = current_year - hire_year
        values = {
            "employee": employee_sudo,
            "main_object": employee_sudo,
            "hide_sidebar": True,
            "years_in_company": years_in_company,
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


    @http.route("/notify/absence", type="json", auth="user", methods=["POST"], website=True)
    def notify_absence(self, **kwargs):
        user = request.env.user
        employee = user.employee_id

        if not employee:
            _logger.warning("⚠️ Usuario sin empleado vinculado: %s", user.name)
            return {"error": "Tu usuario no está vinculado a un empleado."}

        try:
            _logger.warning("✅ Iniciando proceso de notificación para %s", employee.name)

            # 1. Obtener tipo de ausencia por ID
            leave_type = request.env['hr.leave.type'].sudo().search([
    ('name', '=', 'Ausencias por enfermedad'),
    ('company_id', 'in', [False, user.company_id.id])
], limit=1)
            if not leave_type:
                _logger.warning("❌ No se encontró el tipo de ausencia.")
                return {"error": "No se encontró el tipo de ausencia por enfermedad."}
            _logger.warning("✅ Tipo de ausencia obtenido: %s", leave_type.name)

            today = fields.Date.today()
            _logger.warning("📅 Fecha de hoy: %s", today)

            # 2. Crear ausencia
            leave = request.env['hr.leave'].sudo().create({
                "name": f"Ausencia por enfermedad - {employee.name}",
                "employee_id": employee.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": today,
                "request_date_to": today,
                "number_of_days": 1,
            })
            _logger.warning("✅ Ausencia creada con ID: %s", leave.id)

            # 3. Obtener o crear canal de RRHH
            channel_name = "Notificaciones por Enfermedad"
            channel = request.env['discuss.channel'].sudo().search([
                ("name", "=", channel_name)
            ], limit=1)

            if not channel:
                _logger.warning("ℹ️ Canal no existe. Creando canal de RRHH.")
                channel = request.env['discuss.channel'].sudo().create({
                    "name": channel_name,
                    "channel_type": "channel",
                    "group_ids": [(6, 0, [request.env.ref('hr.group_hr_user').id])],
                    "channel_partner_ids": [] 
                })
            _logger.warning("✅ Canal RRHH disponible: %s", channel.name)

            # 4. Publicar mensaje en canal
            message = f"📢 El colaborador {employee.name.upper()} ha notificado una AUSENCIA POR ENFERMEDAD para hoy ({today})."
            channel.message_post(
                body=message,
                message_type="comment",
                subtype_xmlid="mail.mt_note"
            )
            _logger.warning("✅ Mensaje publicado en canal.")

            return {
                "success": True,
                "message": "✅ Notificación de ausencia enviada correctamente."
            }

        except Exception as e:
            import traceback
            _logger.error("❌ Error completo en notify_absence:\n%s", traceback.format_exc())
            return {"error": "No se pudo procesar la solicitud."}


    @http.route("/prueba/ping", type="json", auth="user", methods=["POST"], website=True)
    def prueba_ping(self, **kwargs):
        return {"pong": True}
    
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
            publication = request.env[res_model].sudo().browse(int(res_id))
            if not publication.exists():
                return {'success': False, 'error': 'El documento no fue encontrado.'}
            
            Log = request.env['publication.view.log'].sudo()
            current_user = request.env.user

            already_read = Log.search_count([
                ('res_model', '=', res_model),
                ('res_id', '=', int(res_id)),
                ('user_id', '=', current_user.id)
            ]) > 0

            if not already_read:
                Log.create({
                    'res_model': res_model,
                    'res_id': int(res_id),
                    'user_id': current_user.id,
                })

            return {'success': True}
            
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
    
    @http.route("/news", type="http", auth="public", website=True)
    def render_news(self, **kwargs):
        articles = request.env["news.article"].sudo().search([], order="published_date desc", limit=5)
        values = { "news_articles": articles, "hide_sidebar": True}
        
        return request.render("mi_website_ext.news_template", values)
        
    @http.route('/', type='http', auth='user', website=True)
    def render_home(self, **kwargs):
        user = request.env.user
        user._compute_remunerated_permission_hours()
        return request.render('mi_website_ext.custom_sidebar', {
            'user': user,
        })

    
class TermsController(Controller):
    @http.route('/portal/accept_terms', type='json', auth='user', website=True, methods=['POST'])
    def accept_terms(self):
        user = request.env.user
        user.sudo().x_terms_accepted = True
        return {'success': True}

    @http.route('/portal/terms_status', type='json', auth='user', website=True)
    def terms_status(self):
        user = request.env.user
        return {'accepted': bool(user.sudo().x_terms_accepted)}
    
class PolicyController(http.Controller):

    @http.route('/portal/mandatory_policies_status', type='json', auth='user', website=True)
    def get_mandatory_policies_status(self, **kwargs):
        user = request.env.user
        Policy = request.env['website.publication'].sudo()
        
        if user.sudo().x_has_accepted_policies:
            return {'user_already_accepted': True}

        all_policies = Policy.search([
            ('publication_type', '=', 'policy'),
            ('is_published', '=', True),
        ])

        if not all_policies:
            return {'no_policies': True}

        read_logs = request.env['publication.view.log'].sudo().search([
            ('user_id', '=', user.id),
            ('res_model', '=', 'website.publication'),
            ('res_id', 'in', all_policies.ids),
        ])
        read_policy_ids = read_logs.mapped('res_id')

        policies_data = [{'id': p.id, 'name': p.name, 'url': p.attachment_url} for p in all_policies]

        return {
            'user_already_accepted': False,
            'policies': policies_data,
            'read_policy_ids': read_policy_ids,
            'all_policies_read': len(read_policy_ids) == len(all_policies.ids)
        }

    @http.route('/portal/confirm_all_policies_read', type='json', auth='user', website=True)
    def confirm_all_policies_read(self, **kwargs):
        try:
            request.env.user.sudo().write({'x_has_accepted_policies': True})
            return {'success': True}
        except Exception as e:
            _logger.error(f"Error al confirmar políticas: {e}")
            return {'success': False}
        
class ProfileUpdateController(http.Controller):
    
    @http.route('/portal/profile_update_status', type='json', auth='user', website=True)
    def get_profile_update_status(self, **kwargs):
        user = request.env.user.sudo()
        user.invalidate_recordset(['x_has_updated_profile'])
        user_sudo = user.sudo()
        return {
            'requires_update': not user_sudo.x_has_updated_profile
        }

    @http.route('/portal/confirm_profile_updated', type='json', auth='user', website=True)
    def confirm_profile_updated(self, **kwargs):
        try:
            request.env.user.sudo().write({'x_has_updated_profile': True})
            return {'success': True}
        except Exception:
            return {'success': False, 'error': 'No se pudo guardar la confirmación.'}
