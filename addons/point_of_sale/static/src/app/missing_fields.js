import { Component, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
// so this is a workaround such that we don't have console warnings

class DefaultField extends Component {
    static template = xml``;
    static props = ["*"];
}
registry
    .category("fields")
    .add("list.many2one_avatar_user", { component: DefaultField });
registry.category("fields").add("list.list_activity", { component: DefaultField });
