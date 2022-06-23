/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { formatSelection } from "../formatters";

const { Component } = owl;

export class StateSelectionField extends Component {
    setup() {
        if (this.props.addCommand) {
            this.initiateCommand();
        }
        this.excludedValues = [];
        this.colorPrefix = "o_status_";
        this.colors = {
            blocked: "red",
            done: "green",
        };
    }
    get availableOptions() {
        return this.props.options.filter((o) => !this.excludedValues.includes(o[0]));
    }
    get currentValue() {
        return this.props.value || this.props.options[0][0];
    }
    get label() {
        return formatSelection(this.currentValue, { selection: this.props.options });
    }

    initiateCommand() {
        try {
            const commandService = useService("command");
            const provide = () => {
                return this.props.options.map((value) => ({
                    name: value[1],
                    action: () => {
                        this.props.update(value[0]);
                    },
                }));
            };
            const name = this.env._t("Set kanban state...");
            const action = () => {
                return commandService.openPalette({
                    placeholder: this.env._t("Set a kanban state..."),
                    providers: [{ provide }],
                });
            };
            const options = {
                category: "smart_action",
                hotkey: "alt+shift+r",
            };
            commandService.add(name, action, options);
        } catch {
            console.log("Could not add command to service");
        }
    }
    statusColor(value) {
        return this.colors[value] ? this.colorPrefix + this.colors[value] : "";
    }
}

StateSelectionField.template = "web.StateSelectionField";
StateSelectionField.components = {
    Dropdown,
    DropdownItem,
};
StateSelectionField.props = {
    ...standardFieldProps,
    addCommand: { type: Boolean, optional: true },
    showLabel: { type: Boolean, optional: true },
    options: Object,
};
StateSelectionField.defaultProps = {
    addCommand: false,
    showLabel: false,
};

StateSelectionField.displayName = _lt("Label Selection");
StateSelectionField.supportedTypes = ["selection"];

StateSelectionField.extractProps = (fieldName, record, attrs) => {
    return {
        addCommand: record.activeFields[fieldName].viewType === "form",
        showLabel: record.activeFields[fieldName].viewType === "list" && !attrs.options.hide_label,
        options: Array.from(record.fields[fieldName].selection),
        readonly: record.isReadonly(fieldName),
    };
};

registry.category("fields").add("state_selection", StateSelectionField);
registry.category("fields").add("list.state_selection", StateSelectionField);
