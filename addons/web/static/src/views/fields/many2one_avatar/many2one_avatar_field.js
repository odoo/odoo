import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "../many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    Many2OneField,
} from "../many2one/many2one_field";

export class Many2OneAvatarField extends Component {
    static template = "web.Many2OneAvatarField";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        return computeM2OProps(this.props);
    }
}

export const many2OneAvatarField = {
    ...buildM2OFieldDescription(Many2OneAvatarField),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            canOpen:
                "no_open" in staticInfo.options
                    ? !staticInfo.options.no_open
                    : staticInfo.viewType === "form",
        };
    },
};

registry.category("fields").add("many2one_avatar", many2OneAvatarField);
