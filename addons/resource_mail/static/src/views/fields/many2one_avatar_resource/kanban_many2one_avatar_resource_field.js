import { Component } from "@odoo/owl";
import { AvatarResource } from "@resource_mail/components/avatar_resource/avatar_resource";
import { registry } from "@web/core/registry";
import { computeM2OProps, KanbanMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class KanbanMany2OneAvatarResourceField extends Component {
    static template = "resource_mail.KanbanMany2OneAvatarResourceField";
    static components = { AvatarResource, KanbanMany2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            specification: {
                resource_type: {},
            },
        };
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
export const kanbanMany2OneAvatarResourceField = {
    ...buildM2OFieldDescription(KanbanMany2OneAvatarResourceField),
    additionalClasses: ["o_field_many2one_avatar_kanban", "o_field_many2one_avatar"],
    fieldDependencies: [
        { name: "display_name", type: "char" },
        // to add in model that will use this widget for m2o field related to resource.resource record (as related field is only supported for x2m)
        { name: "resource_type", type: "selection" },
    ],
};

registry
    .category("fields")
    .add("kanban.many2one_avatar_resource", kanbanMany2OneAvatarResourceField);
