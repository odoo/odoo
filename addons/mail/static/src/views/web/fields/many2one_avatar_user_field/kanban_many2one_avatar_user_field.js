import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useMany2One } from "@web/views/fields/many2one/many2one";
import { Avatar } from "../avatar/avatar";

export class KanbanMany2OneAvatarUserField extends Component {
    static template = `mail.${this.name}`;
    static components = { Avatar };
    static props = ["*"];
    static defaultProps = {};

    setup() {
        this.controller = useMany2One(() => this.props);
    }
}

registry.category("fields").add("kanban.many2one_avatar_user", {
    component: KanbanMany2OneAvatarUserField,
    extractProps({ options }) {
        return {
            displayAvatarName: options.display_avatar_name || false,
        };
    },
});
