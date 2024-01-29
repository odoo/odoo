import { Component } from "@odoo/owl";
import { useCommand } from "@web/core/commands/command_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatSelection } from "../formatters";
import { standardFieldProps } from "../standard_field_props";

export class StateSelectionField extends Component {
    static template = "web.StateSelectionField";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        ...standardFieldProps,
        showLabel: { type: Boolean, optional: true },
        withCommand: { type: Boolean, optional: true },
        autosave: { type: Boolean, optional: true },
    };
    static defaultProps = {
        showLabel: true,
    };

    setup() {
        this.colorPrefix = "o_status_";
        this.colors = {
            blocked: "red",
            done: "green",
        };
        if (this.props.withCommand) {
            const hotkeys = ["D", "F", "G"];
            for (const [index, [value, label]] of this.options.entries()) {
                useCommand(
                    _t("Set kanban state as %s", label),
                    () => {
                        this.updateRecord(value);
                    },
                    {
                        category: "smart_action",
                        hotkey: hotkeys[index] && "alt+" + hotkeys[index],
                        isAvailable: () => this.props.record.data[this.props.name] !== value,
                    }
                );
            }
        }
    }
    get options() {
        return this.props.record.fields[this.props.name].selection.map(([state, label]) => {
            return [state, this.props.record.data[`legend_${state}`] || label];
        });
    }
    get currentValue() {
        return this.props.record.data[this.props.name] || this.options[0][0];
    }
    get label() {
        if (
            this.props.record.data[this.props.name] &&
            this.props.record.data[`legend_${this.props.record.data[this.props.name][0]}`]
        ) {
            return this.props.record.data[`legend_${this.props.record.data[this.props.name][0]}`];
        }
        return formatSelection(this.currentValue, { selection: this.options });
    }

    statusColor(value) {
        return this.colors[value] ? this.colorPrefix + this.colors[value] : "";
    }

    async updateRecord(value) {
        await this.props.record.update({ [this.props.name]: value }, { save: this.props.autosave });
    }
}

export const stateSelectionField = {
    component: StateSelectionField,
    displayName: _t("Label Selection"),
    supportedOptions: [
        {
            label: _t("Autosave"),
            name: "autosave",
            type: "boolean",
            default: true,
            help: _t(
                "If checked, the record will be saved immediately when the field is modified."
            ),
        },
        {
            label: _t("Hide label"),
            name: "hide_label",
            type: "boolean",
        },
    ],
    supportedTypes: ["selection"],
    extractProps({ options, viewType }, dynamicInfo) {
        return {
            showLabel: 'hide_label' in options ? !options.hide_label : false,
            withCommand: viewType === "form",
            readonly: dynamicInfo.readonly,
            autosave: "autosave" in options ? !!options.autosave : true,
        };
    },
};

registry.category("fields").add("state_selection", stateSelectionField);
