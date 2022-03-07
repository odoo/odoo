/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { debounce } from "@web/core/utils/timing";
import { standardFieldProps } from "./standard_field_props";
import { parseFloat } from "./parsers";

const { Component, onWillUpdateProps, useState } = owl;

export class ProgressBarField extends Component {
    setup() {
        this.state = useState({
            currentValue: this.getInitialValue("currentValue"),
            maxValue: this.getInitialValue("maxValue"),
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                Object.assign(this.state, {
                    currentValue: this.getInitialValue("currentValue"),
                    maxValue: this.getInitialValue("maxValue"),
                });
            }
        });
    }
    getInitialValue(part) {
        if (this.props[part]) {
            let value;
            try {
                value = this.props.parse(this.props[part]);
            } catch {
                value =
                    (this.props.record.data[this.props[part]] !== undefined &&
                        this.props.record.data[this.props[part]]) ||
                    0;
            }
            return value;
        }
        return part === "maxValue" ? 100 : this.props.record.data[this.props.name] || 0;
    }

    /**
     * @param {String} value
     * @param {String} part
     */
    onChangeValue(value, part) {
        let parsedValue;
        try {
            parsedValue = parseFloat(value);
            if (this.props.type === "integer") {
                parsedValue = Math.floor(parsedValue);
            }
            this.state[part] = parsedValue;
        } catch {
            this.props.setAsInvalid(this.props.name);
            return;
        }
        this.props.update(parsedValue, part);
    }
    onKeyDownValue() {
        debounce.apply(this, [this.updateStateValue, 100]);
    }

    /**
     * @param {Event} ev
     * @param {String} part
     */
    updateStateValue(ev, part) {
        try {
            this.state[part] = parseFloat(ev.target.value);
        } catch {}
    }
}

ProgressBarField.defaultProps = {
    setAsInvalid: () => {},
};
ProgressBarField.props = {
    ...standardFieldProps,
    currentValue: { type: String, optional: true },
    maxValue: { type: String, optional: true },
    isCurrentValueEditable: { type: Boolean, optional: true },
    isMaxValueEditable: { type: Boolean, optional: true },
    setAsInvalid: { type: Function, optional: true },
};
ProgressBarField.template = "web.ProgressBarField";
ProgressBarField.extractProps = (fieldName, record, attrs) => {
    const values = {
        currentValue: attrs.options.current_value,
        maxValue: attrs.options.max_value,
    };
    return {
        ...values,
        isCurrentValueEditable:
            (attrs.options.editable && !attrs.options.edit_max_value) ||
            attrs.options.edit_current_value,
        isMaxValueEditable: attrs.options.edit_max_value,
        setAsInvalid: record.setInvalidField.bind(record),
        update: (value, part) => {
            if (record.data[values[part]] !== undefined) {
                record.update(values[part], value);
            } else {
                record.update(fieldName, value);
            }
        },
    };
};
ProgressBarField.displayName = _lt("Progress Bar");
ProgressBarField.supportedTypes = ["integer", "float"];

registry.category("fields").add("progressbar", ProgressBarField);
