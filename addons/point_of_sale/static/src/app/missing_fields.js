import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";

// In pos we are not loading all the assests that the web views might need
// so this is a workaround such that we don't have console warnings

class DefaultField extends Component {
    static template = xml``;
    static props = ["*"];
}
registry.category("fields").add("list.many2one_avatar_user", { component: DefaultField });
registry.category("fields").add("list.list_activity", { component: DefaultField });
registry.category("fields").add("x2many_buttons", { component: DefaultField });
registry.category("fields").add("field_partner_autocomplete", { component: DefaultField });
registry.category("fields").add("res_partner_many2one", { component: DefaultField });
registry.category("fields").add("many2one_avatar_user", { component: DefaultField });
registry.category("fields").add("auto_save_res_partner", { component: DefaultField });
registry.category("fields").add("website_redirect_button", { component: DefaultField });
