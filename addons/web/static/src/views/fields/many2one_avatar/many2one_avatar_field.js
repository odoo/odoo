import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "../many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    many2OneFieldProps,
} from "../many2one/many2one_field";

export class Many2OneAvatarField extends Component {
    static template = "web.Many2OneAvatarField";
    static components = { Many2One };
    props = useProps(many2OneFieldProps);

    get m2oProps() {
        return computeM2OProps(this.props);
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get uniqueId() {
        return this.value?.write_date ? this.value.write_date.toMillis() : undefined;
    }
}

export const many2OneAvatarField = {
    ...buildM2OFieldDescription(Many2OneAvatarField),
    relatedFields: [{ name: "write_date", type: "datetime" }],
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
