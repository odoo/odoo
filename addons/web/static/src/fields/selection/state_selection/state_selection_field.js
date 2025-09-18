// @ts-check

/** @module @web/fields/selection/state_selection/state_selection_field - Kanban-style colored state dot dropdown for Selection columns */

import { Component } from "@odoo/owl";
import { CheckboxItem } from "@web/components/dropdown/checkbox_item";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatSelection } from "@web/fields/formatters";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { useCommand } from "@web/services/commands/command_hook";

export class StateSelectionField extends Component {
    static template = "web.StateSelectionField";
    static components = {
        Dropdown,
        CheckboxItem,
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
                        hotkey: hotkeys[index] && `alt+${hotkeys[index]}`,
                        isAvailable: () =>
                            this.props.record.data[this.props.name] !== value,
                    },
                );
            }
        }
    }
    /** @returns {Array<[string, string]>} Selection options with legend label overrides */
    get options() {
        return this.props.record.fields[this.props.name].selection.map(
            ([state, label]) => [
                state,
                this.props.record.data[`legend_${state}`] || label,
            ],
        );
    }
    /** @returns {string} Current state value or first option as default */
    get currentValue() {
        return this.props.record.data[this.props.name] || this.options[0][0];
    }
    /** @returns {string} Display label with legend override if available */
    get label() {
        if (
            this.props.record.data[this.props.name] &&
            this.props.record.data[
                `legend_${this.props.record.data[this.props.name][0]}`
            ]
        ) {
            return this.props.record.data[
                `legend_${this.props.record.data[this.props.name][0]}`
            ];
        }
        return formatSelection(this.currentValue, { selection: this.options });
    }

    /**
     * @param {string} value State value (e.g. "blocked", "done")
     * @returns {string} CSS color class for the status dot
     */
    statusColor(value) {
        return this.colors[value] ? this.colorPrefix + this.colors[value] : "";
    }

    /** @param {string} value New state value to set on the record */
    async updateRecord(value) {
        await this.props.record.update(
            { [this.props.name]: value },
            { save: this.props.autosave },
        );
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
                "If checked, the record will be saved immediately when the field is modified.",
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
            showLabel: "hide_label" in options ? !options.hide_label : false,
            withCommand: viewType === "form",
            readonly: dynamicInfo.readonly,
            autosave: "autosave" in options ? !!options.autosave : true,
        };
    },
};

registry.category("fields").add("state_selection", stateSelectionField);
