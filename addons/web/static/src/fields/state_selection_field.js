/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class StateSelectionField extends Component {
    get colorClass() {
        if (this.props.value === "blocked") {
            return "o_status_red";
        } else if (this.props.value === "done") {
            return "o_status_green";
        }
        return "";
    }
    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }
    get label() {
        if (this.props.value === "blocked") {
            return "Blocked";
        } else if (this.props.value === "done") {
            return "Done";
        }
        return "Normal";
    }
    get options() {
        return this.props.record.fields[this.props.name].selection;
    }

    /**
     * @param {Event} ev
     */
    onChange(value) {
        this.props.update(value);
    }
}

StateSelectionField.template = "web.StateSelectionField";
StateSelectionField.components = {
    Dropdown,
    DropdownItem,
};
StateSelectionField.defaultProps = {
    hideLabel: false,
};
StateSelectionField.props = {
    ...standardFieldProps,
    hideLabel: { type: Boolean, optional: true },
};
StateSelectionField.displayName = _lt("Label Selection");
StateSelectionField.supportedTypes = ["selection"];
StateSelectionField.convertAttrsToProps = (attrs) => {
    return {
        hideLabel: attrs.options.hide_label,
    };
};
registry.category("fields").add("state_selection", StateSelectionField);
