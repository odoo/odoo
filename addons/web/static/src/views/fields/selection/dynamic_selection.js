import { Component, onWillRender } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class DynamicSelectionField extends Component {
    static template = "web.SelectionField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        selectionField: { type: String },
        required: { type: Boolean, optional: true },
    };

    get value() {
        let val = this.props.record.data[this.props.name];
        val = val && val.trim();
        return val ? val : false;
    }

    setup() {
        onWillRender(() => {
            const selFieldType = this.props.record.fields[this.props.selectionField].type;
            let selFieldValue = this.props.record.data[this.props.selectionField];
            if (selFieldType === "char") {
                selFieldValue = JSON.parse((selFieldValue && selFieldValue.trim()) || "{}");
            }
            let selectionItems = selFieldValue || {};
            if (Array.isArray(selFieldValue)) {
                selectionItems = Object.fromEntries(
                    selFieldValue.map((tuple) => [tuple[0], tuple[1]])
                );
            }

            this.options = [];
            const value = this.value;
            if (value && !(value in selectionItems)) {
                this.options.push([value, value]);
            }
            for (const [k, v] of Object.entries(selectionItems)) {
                this.options.push([k, this.getOptionText(k, v)]);
            }
        });
    }

    onChange(ev) {
        const value = JSON.parse(ev.target.value);
        this.props.record.update({ [this.props.name]: value });
    }

    getOptionText(key, value) {
        return value && value !== key ? `${value} (${key})` : value;
    }

    stringify(value) {
        return JSON.stringify(value);
    }
}

registry.category("fields").add("char_dynamic_selection", {
    component: DynamicSelectionField,
    displayName: _t("Dynamic Selection"),
    supportedTypes: ["char"],
    isEmpty: (record, fieldName) => !record.data[fieldName] || !record.data[fieldName].trim(),
    extractProps({ attrs, options, viewType }, dynamicInfo) {
        const props = {
            placeholder: attrs.placeholder,
            selectionField: options.selection_field,
            required: dynamicInfo.required,
        };
        if (viewType === "kanban") {
            props.readonly = dynamicInfo.readonly;
        }
        return props;
    },
});
