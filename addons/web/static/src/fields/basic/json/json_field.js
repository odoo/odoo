// @ts-check

/** @module @web/fields/basic/json/json_field - Read-only display field for JSON columns */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatJson } from "@web/fields/formatters";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class JsonField extends Component {
    static template = "web.JsonField";
    static props = {
        ...standardFieldProps,
    };
    /** @returns {string} pretty-printed JSON string */
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
