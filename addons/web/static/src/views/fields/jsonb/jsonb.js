import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

export class JsonField extends Component {
    static template = "web.JsonbField";
    static props = {
        ...standardFieldProps,
    };
    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        return value ? JSON.stringify(value) : "";
    }
}

export const jsonField = {
    component: JsonField,
    displayName: _t("Json"),
    supportedTypes: ["jsonb"],
};

registry.category("fields").add("jsonb", jsonField);
