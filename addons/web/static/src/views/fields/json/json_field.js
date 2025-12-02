import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";
import { formatJson } from "@web/views/fields/formatters";

import { Component } from "@odoo/owl";

export class JsonField extends Component {
    static template = "web.JsonField";
    static props = {
        ...standardFieldProps,
    };
    get formattedValue() {
        return formatJson(this.props.record.data[this.props.name]);
    }
}

export const jsonField = {
    component: JsonField,
    displayName: _t("Json"),
    supportedTypes: ["json"],
};

registry.category("fields").add("json", jsonField);
