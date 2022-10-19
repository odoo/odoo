/** @odoo-module **/

import { useCommand } from "@web/core/commands/command_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { formatSelection } from "../formatters";

import { Component } from "@odoo/owl";

export class StateSelectionField extends Component {
    setup() {
        if (this.props.record.activeFields[this.props.name].viewType === "form") {
            const commandName = this.env._t("Set kanban state...");
            useCommand(
                commandName,
                () => {
                    return {
                        placeholder: commandName,
                        providers: [
                            {
                                provide: () =>
                                    this.options.map((value) => ({
                                        name: value[1],
                                        action: () => {
                                            this.props.update(value[0]);
                                        },
                                    })),
                            },
                        ],
                    };
                },
                { category: "smart_action", hotkey: "alt+shift+r" }
            );
        }
        this.colorPrefix = "o_status_";
        this.colors = {
            blocked: "red",
            done: "green",
        };
    }
    get options() {
        return this.props.record.fields[this.props.name].selection.map(([state, label]) => {
            return [state, this.props.record.data[`legend_${state}`] || label];
        });
    }
    get availableOptions() {
        return this.options.filter((o) => o[0] !== this.currentValue);
    }
    get currentValue() {
        return this.props.value || this.options[0][0];
    }
    get label() {
        if (this.props.value && this.props.record.data[`legend_${this.props.value[0]}`]) {
            return this.props.record.data[`legend_${this.props.value[0]}`];
        }
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
