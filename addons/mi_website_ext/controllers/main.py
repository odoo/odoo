from odoo import http
from odoo.http import request


class WebsiteCustom(http.Controller):
    @http.route(["/abrir_bio_editor"], type="json", auth="user")
    def abrir_bio_editor(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "mi_website_ext.bio_editor.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_bio": request.env.user.bio,
            },
        }

    @http.route("/galeria", type="http", auth="public", website=True)
    def render_gallery(self, **kwargs):
        return request.render("mi_website_ext.gallery_template")

    @http.route("/blogs", type="http", auth="public", website=True)
    def render_blog(self, **kwargs):
        return request.render("mi_website_ext.blog_template")

    @http.route("/news", type="http", auth="public", website=True)
    def render_news(self, **kwargs):
        return request.render("mi_website_ext.news_template")

    @http.route("/task", type="http", auth="public", website=True)
    def render_task(self, **kwargs):
        return request.render("mi_website_ext.task_template")

    @http.route("/policy", type="http", auth="public", website=True)
    def render_policy(self, **kwargs):
        return request.render("mi_website_ext.policy_template")

    @http.route("/birthday_single", type="http", auth="public", website=True)
    def render_birthday_single(self, **kwargs):
        return request.render("mi_website_ext.birthday_single_template")

    @http.route("/birthday_all", type="http", auth="public", website=True)
    def render_birthday_all(self, **kwargs):
        return request.render("mi_website_ext.birthday_all_template")

    @http.route("/announce", type="http", auth="public", website=True)
    def render_announce(self, **kwargs):
        return request.render("mi_website_ext.announce_template")

    @http.route("/activity", type="http", auth="public", website=True)
    def render_activity(self, **kwargs):
        return request.render("mi_website_ext.activity_template")

    @http.route("/activity_all", type="http", auth="public", website=True)
    def render_activity_all(self, **kwargs):
        return request.render("mi_website_ext.activity_all_template")

    @http.route("/anniversary", type="http", auth="public", website=True)
    def render_anniversary(self, **kwargs):
        return request.render("mi_website_ext.anniversary_single_template")

    @http.route("/anniversary_all", type="http", auth="public", website=True)
    def render_anniversary_all(self, **kwargs):
        return request.render("mi_website_ext.anniversary_all_template")

    @http.route("/program", type="http", auth="public", website=True)
    def render_program(self, **kwargs):
        return request.render("mi_website_ext.program")

    @http.route("/intern_all", type="http", auth="public", website=True)
    def render_intern_all(self, **kwargs):
        return request.render("mi_website_ext.intern_all_template")
