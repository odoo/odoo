import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, KanbanMany2One } from "../many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "../many2one/many2one_field";

export class KanbanMany2OneAvatarField extends Component {
    static template = "web.KanbanMany2OneAvatarField";
    static components = { KanbanMany2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        return computeM2OProps(this.props);
    }
}

registry.category("fields").add("kanban.many2one_avatar", {
    ...buildM2OFieldDescription(KanbanMany2OneAvatarField),
    additionalClasses: ["o_field_many2one_avatar_kanban"],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            readonly: dynamicInfo.readonly,
        };
    },
});
