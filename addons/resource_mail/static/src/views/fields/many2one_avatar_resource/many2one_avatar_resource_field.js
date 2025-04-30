import { Component } from "@odoo/owl";
import { AvatarResource } from "@resource_mail/components/avatar_resource/avatar_resource";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, extractM2OFieldProps, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class Many2OneAvatarResourceField extends Component {
    static template = "resource_mail.Many2OneAvatarResourceField";
    static components = { AvatarResource, Many2One };
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
export const many2OneAvatarResourceField = {
    ...buildM2OFieldDescription(Many2OneAvatarResourceField),
    additionalClasses: ["o_field_many2one_avatar"],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            canOpen: "no_open" in staticInfo.options
                ? !staticInfo.options.no_open
                : staticInfo.viewType === "form",
        };
    },
    fieldDependencies: [
        { name: "display_name", type: "char" },
        // to add in model that will use this widget for m2o field related to resource.resource record (as related field is only supported for x2m)
        { name: "resource_type", type: "selection" },
    ],
};

registry.category("fields").add("many2one_avatar_resource", many2OneAvatarResourceField);
