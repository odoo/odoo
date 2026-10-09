import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { formatJson } from "@web/views/fields/formatters";
import { validFieldTypes } from "@web/views/fields/field";

import { Component } from "@odoo/owl";

validFieldTypes.serialized = { availableOffline: true };

export function formatSerialized(value) {
    return formatJson(value);
}

export class SerializedField extends Component {
    static template = "base_sparse_field.SerializedField";
    static props = {
        ...standardFieldProps,
    };
    get formattedValue() {
        return formatSerialized(this.props.record.data[this.props.name]);
    }
}

export const serializedField = {
    component: SerializedField,
    displayName: _t("Serialized"),
    supportedTypes: ["serialized"],
};

registry.category("fields").add("serialized", serializedField);
registry.category("formatters").add("serialized", formatSerialized);
