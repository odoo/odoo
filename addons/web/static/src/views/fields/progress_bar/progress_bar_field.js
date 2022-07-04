/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { parseFloat } from "../parsers";
import { standardFieldProps } from "../standard_field_props";
import { useNumpadDecimal } from "../numpad_decimal_hook";

const { Component, onWillUpdateProps, useState } = owl;
const formatters = registry.category("formatters");
const parsers = registry.category("parsers");

export class ProgressBarField extends Component {
    setup() {
        useNumpadDecimal();
        this.state = useState({
            currentValue: this.props.currentValue.value,
            maxValue: this.props.maxValue.value,
            isEditing: false,
        });
        onWillUpdateProps((nextProps) => {
            Object.assign(this.state, {
                currentValue: nextProps.currentValue.value,
                maxValue: nextProps.maxValue.value,
            });
            if (nextProps.readonly) {
                this.state.isEditing = false;
            }
        });
    }

    getFormattedValue(part, humanReadable = false) {
        const formatter = formatters.get(this.props[part].type);
        return formatter(this.state[part], { humanReadable });
    }

    /**
     * @param {String} value
     * @param {String} part
     */
    onChangeValue(value, part) {
        try {
            let parsedValue = parseFloat(value);
            if (this.props[part].type === "integer") {
                parsedValue = Math.floor(parsedValue);
            }
            this.state[part] = parsedValue;
            this.props.updatePart(part, parsedValue);
            if (this.props.readonly) {
                this.state.isEditing = false;
                this.props.record.save();
            }
        } catch {
            this.props.invalidate();
            return;
        }
    }

    onClick() {
        if (this.props.isEditable && (!this.props.readonly || this.props.isEditableInReadonly)) {
            this.state.isEditing = true;
        }
    }

    onBlur() {
        if (this.props.readonly) {
            this.state.isEditing = false;
        }
    }

    onInput(ev, part) {
        const parser = parsers.get(this.props[part].type);
        try {
            this.state[part] = parser(ev.target.value);
        } catch {
            // pass
        }
    }
}

ProgressBarField.template = "web.ProgressBarField";
ProgressBarField.props = {
    ...standardFieldProps,
    currentValue: { type: Object, optional: true },
    isPercentage: { type: Boolean, optional: true },
    maxValue: { type: Object, optional: true },
    isEditable: { type: Boolean, optional: true },
    isEditableInReadonly: { type: Boolean, optional: true },
    isCurrentValueEditable: { type: Boolean, optional: true },
    isMaxValueEditable: { type: Boolean, optional: true },
    invalidate: { type: Function, optional: true },
    updatePart: { type: Function, optional: true },
};
ProgressBarField.defaultProps = {
    invalidate: () => {},
    updatePart: () => {},
};

ProgressBarField.displayName = _lt("Progress Bar");
ProgressBarField.supportedTypes = ["integer", "float"];

ProgressBarField.extractProps = (fieldName, record, attrs) => {
    const getPart = (part) => {
        if (attrs.options[part]) {
            let value = attrs.options[part];
            let name;
            if (isNaN(value)) {
                value =
                    (record.data[attrs.options[part]] !== undefined &&
                        record.data[attrs.options[part]]) ||
                    0;
                name = attrs.options[part];
            }
            return {
                fieldName: name,
                value,
                type: value % 1 === 0 ? "integer" : "float",
            };
        }
        const value = part === "max_value" ? 100 : record.data[fieldName] || 0;
        return {
            fieldName: fieldName,
            value,
            type: value % 1 === 0 ? "integer" : "float",
        };
    };
    const parts = {
        currentValue: getPart("current_value"),
        maxValue: getPart("max_value"),
    };
    return {
        ...parts,
        isPercentage: !attrs.options.max_value,
        isEditable: attrs.options.editable,
        isEditableInReadonly: attrs.options.editable_readonly,
        isCurrentValueEditable:
            attrs.options.editable &&
            (!attrs.options.edit_max_value || attrs.options.edit_current_value),
        isMaxValueEditable: attrs.options.editable && attrs.options.edit_max_value,
        invalidate: () => record.setInvalidField(fieldName),
        updatePart: (part, value) => record.update({ [parts[part].fieldName]: value }),
    };
};

registry.category("fields").add("progressbar", ProgressBarField);
