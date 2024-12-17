import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { Component } from "@odoo/owl";
import { AvatarCardResourcePopover } from "@resource_mail/components/avatar_card_resource/avatar_card_resource_popover";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

class AvatarResource extends Avatar {
    static components = { ...Avatar.components, Popover: AvatarCardResourcePopover };
}

class Many2OneAvatarResourceField extends Component {
    static template = "resource_mail.Many2OneAvatarResourceField";
    static components = { Many2One, AvatarResource };
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

registry.category("fields").add("many2one_avatar_resource", {
    ...buildM2OFieldDescription(Many2OneAvatarResourceField),
    fieldDependencies: [
        { name: "display_name", type: "char" },
        // to add in model that will use this widget for m2o field related to resource.resource record (as related field is only supported for x2m)
        { name: "resource_type", type: "selection" },
    ],
});
