from odoo import http
from odoo.http import request, route


class MainMenuController(http.Controller):

    @route("/main_menu/announcement", methods=["POST"], type="jsonrpc", auth="user")
    def get_company_information(self, **kwargs):
        company = request.env["res.company"].browse(kwargs.get("company_id"))
        return {
            "showWidgets": company.show_widgets,
            "announcement": company.announcement or "",
            "userIsAdmin": request.env.user.has_group("base.group_system")
        }

    @route("/main_menu/announcement/save", methods=["POST"], type="jsonrpc", auth="user")
    def menu_save_announcement(self, **kwargs):
        company = request.env["res.company"].browse(kwargs.get("company_id"))
        return company.write(kwargs.get("data"))

    @route("/main_menu/bookmark", methods=["POST"], type="jsonrpc", auth="user")
    def get_bookmarks_by_user(self, **kwargs):
        return request.env["menu.bookmark"].search_read([("user_id", "=", request.env.uid)], [])

    @route("/main_menu/bookmark/add", methods=["POST"], type="jsonrpc", auth="user")
    def add_bookmark(self, **kwargs):
        return request.env["menu.bookmark"].create(kwargs.get("bookmark"))
