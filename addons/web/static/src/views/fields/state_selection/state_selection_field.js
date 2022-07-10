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
        if (this.props.record.activeFields[this.props.name].viewType === "form") {
            this.initiateCommand();
        }
        this.excludedValues = [];
        this.colorPrefix = "o_status_";
        this.colors = {
            blocked: "red",
            done: "green",
        };
    }
    get options() {
        return Array.from(this.props.record.fields[this.props.name].selection);
    }
    get availableOptions() {
        return this.options.filter((o) => !this.excludedValues.includes(o[0]));
    }
    get currentValue() {
        return this.props.value || this.options[0][0];
    }
    get label() {
        return formatSelection(this.currentValue, { selection: this.options });
    }
    get showLabel() {
        return (
            this.props.record.activeFields[this.props.name].viewType === "list" &&
            !this.props.hideLabel
        );
    }
    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }

    initiateCommand() {
        try {
            const commandService = useService("command");
            const provide = () => {
                return this.options.map((value) => ({
                    name: value[1],
                    action: () => {
                        this.props.update(value[0]);
                    },
                }));
            };
            const name = this.env._t("Set kanban state...");
            const action = () => {
                return {
                    placeholder: this.env._t("Set a kanban state..."),
                    providers: [{ provide }],
                };
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
    hideLabel: { type: Boolean, optional: true },
};
StateSelectionField.defaultProps = {
    hideLabel: false,
};

StateSelectionField.displayName = _lt("Label Selection");
StateSelectionField.supportedTypes = ["selection"];

StateSelectionField.extractProps = ({ attrs }) => {
    return {
        hideLabel: !!attrs.options.hide_label,
    };
};

registry.category("fields").add("state_selection", StateSelectionField);
registry.category("fields").add("list.state_selection", StateSelectionField);
