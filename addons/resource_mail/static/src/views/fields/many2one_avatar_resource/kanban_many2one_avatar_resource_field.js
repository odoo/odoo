import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { Component } from "@odoo/owl";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { registry } from "@web/core/registry";
import { KanbanMany2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

class AvatarResource extends Avatar {
    static components = { ...super.components, Popover: AvatarCardResourcePopover };
}

export class KanbanMany2OneAvatarResourceField extends Component {
    static template = "mail.KanbanMany2OneAvatarResourceField";
    static components = { AvatarResource, KanbanMany2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            specification: {
                resource_type: {},
            },
        };
    }

    get resourceType() {
        return this.props.record.data.resource_type;
    }
}

/** @type {import("registries").FieldsRegistryItemShape} */
export const kanbanMany2OneAvatarResourceField = {
    ...buildM2OFieldDescription(KanbanMany2OneAvatarResourceField),
    fieldDependencies: [
        { name: "display_name", type: "char" },
        // to add in model that will use this widget for m2o field related to resource.resource record (as related field is only supported for x2m)
        { name: "resource_type", type: "selection" },
    ],
};

registry
    .category("fields")
    .add("kanban.many2one_avatar_resource", kanbanMany2OneAvatarResourceField);
