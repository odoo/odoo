import { Component, t, useProps } from "@odoo/owl";
import { useCommand } from "@web/core/commands/command_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatSelection } from "../formatters";
import { standardFieldProps } from "../standard_field_props";

export class StateSelectionField extends Component {
    static template = "web.StateSelectionField";
    static components = {
        Dropdown,
        CheckboxItem,
    };
    props = useProps({
        ...standardFieldProps,
        showLabel: t.boolean().optional(true),
        withCommand: t.boolean().optional(),
        viewType: t.string().optional(),
    });

    setup() {
        this.colors = {
            blocked: "danger",
            done: "success",
        };
        this.icons = this.icons || {};
        this.classIcons = this.classIcons || {};
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
        return this.props.record.fields[this.props.name].selection.map(([state, label]) => [
            state,
            this.props.record.data[`legend_${state}`] || label,
        ]);
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
        return this.colors[value] ? `o_status_${this.colors[value]} bg-subtle-${this.colors[value]}` : "text-muted";
    }

    stateIcon(value) {
        return this.icons[value] || "circle";
    }

    stateIconClass(value) {
        return value in this.classIcons ? this.classIcons[value] : this.colors[value] ? "oi-filled" : "";
    }

    async updateRecord(value) {
        await this.props.record.update({ [this.props.name]: value });
    }
}

export const stateSelectionField = {
    component: StateSelectionField,
    displayName: _t("Label Selection"),
    supportedOptions: [
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
            // Type of the arch where this <field> is declared (e.g. "list" for a one2many list
            // inside a form). Use it instead of env.config.viewType, which is the main view ("form").
            viewType,
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("state_selection", stateSelectionField);
