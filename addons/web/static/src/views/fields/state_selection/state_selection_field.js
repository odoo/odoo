/** @odoo-module **/

import { useCommand } from "@web/core/commands/command_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { sprintf } from "@web/core/utils/strings";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { formatSelection } from "../formatters";
import { Component } from "@odoo/owl";

export class StateSelectionField extends Component {
    static template = "web.StateSelectionField";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        ...standardFieldProps,
        hideLabel: { type: Boolean, optional: true },
    };
    static defaultProps = {
        hideLabel: false,
    };

    setup() {
        this.colorPrefix = "o_status_";
        this.colors = {
            blocked: "red",
            done: "green",
        };
        if (this.props.record.activeFields[this.props.name].viewType !== "form") {
            return;
        }
        const hotkeys = ["D", "F", "G"];
        for (const [index, [value, label]] of this.options.entries()) {
            useCommand(
                sprintf(this.env._t("Set kanban state as %s"), label),
                () => this.updateRecord(value),
                {
                    category: "smart_action",
                    hotkey: "alt+" + hotkeys[index],
                    isAvailable: () => this.props.value !== value,
                }
            );
        }
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

    async updateRecord(value) {
        await this.props.record.update({ [this.props.name]: value });
        const rootRecord =
            this.props.record.model.root instanceof this.props.record.constructor &&
            this.props.record.model.root;
        const isInEdition = rootRecord ? rootRecord.isInEdition : this.props.record.isInEdition;
        // We save only if we're on view mode readonly and no readonly field modifier
        if (!isInEdition) {
            return this.props.record.save();
        }
    }
}

export const stateSelectionField = {
    component: StateSelectionField,
    displayName: _lt("Label Selection"),
    supportedTypes: ["selection"],
    extractProps: ({ attrs }) => ({
        hideLabel: !!attrs.options.hide_label,
    }),
};

registry.category("fields").add("state_selection", stateSelectionField);
registry.category("fields").add("list.state_selection", stateSelectionField);
