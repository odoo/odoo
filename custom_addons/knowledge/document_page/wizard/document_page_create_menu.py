# Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class DocumentPageCreateMenu(models.TransientModel):
    """Create Menu."""

    _name = "document.page.create.menu"
    _description = "Wizard Create Menu"

    menu_name = fields.Char(required=True)
    menu_parent_id = fields.Many2one("ir.ui.menu", "Parent Menu", required=True)

    @api.model
    def default_get(self, fields_list):
        """Get Page name of the menu."""
        res = super().default_get(fields_list)
        page_id = self.env.context.get("active_id")
        obj_page = self.env["document.page"]
        page = obj_page.browse(page_id)
        res["menu_name"] = page.name
        return res

    def document_page_menu_create(self):
        """Menu creation."""
        obj_page = self.env["document.page"]
        obj_menu = self.env["ir.ui.menu"]
        obj_action = self.env["ir.actions.act_window"]
        obj_model_data = self.env["ir.model.data"]
        page_id = self.env.context.get("active_id", False)
        page = obj_page.browse(page_id)

        data = self[0]
        view_id = obj_model_data._xmlid_to_res_id("document_page.view_wiki_menu_form")
        value = {
            "name": "Document Page",
            "view_mode": "form,list",
            "res_model": "document.page",
            "view_id": view_id,
            "type": "ir.actions.act_window",
            "target": "current",
        }
        value["domain"] = "[('parent_id','=',%d)]" % page.id
        value["res_id"] = page.id

        # only the super user is allowed to create menu due to security rules
        # on ir.values
        # see.: http://goo.gl/Y99S7V
        action_id = obj_action.sudo().create(value)

        menu_id = obj_menu.sudo().create(
            {
                "name": data.menu_name,
                "parent_id": data.menu_parent_id.id,
                "action": "ir.actions.act_window," + str(action_id.id),
            }
        )
        if page.menu_id:
            page.menu_id.unlink()
        page.write({"menu_id": menu_id.id})
        return {"type": "ir.actions.client", "tag": "reload"}
