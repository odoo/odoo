import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { KanbanMany2One, useMany2One } from "../many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "../many2one/many2one_field";

export class KanbanMany2OneAvatarField extends Component {
    static template = "web.KanbanMany2OneAvatarField";
    static components = { KanbanMany2One };
    static props = {
        ...Many2OneField.props,
        isEditable: { type: Boolean, optional: true },
    };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            readonly: this.props.isEditable,
        };
    }
}

registry.category("fields").add("kanban.many2one_avatar", {
    ...buildM2OFieldDescription(KanbanMany2OneAvatarField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            isEditable: !dynamicInfo.readonly,
        };
    },
});
