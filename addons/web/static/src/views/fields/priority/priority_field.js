import { useCommand } from "@web/core/commands/command_hook";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component, useState } from "@odoo/owl";

export class PriorityField extends Component {
    static template = "web.PriorityField";
    static props = {
        ...standardFieldProps,
        withCommand: { type: Boolean, optional: true },
        autosave: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            index: -1,
        });
        if (this.props.withCommand) {
            for (const command of this.commands) {
                useCommand(...command);
            }
        }
    }

    get commands() {
        const commandName = _t("Set priority...");
        return [
            [
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
                                            this.updateRecord(value[0]);
                                        },
                                    })),
                            },
                        ],
                    };
                },
                { category: "smart_action", hotkey: "alt+r" },
            ],
        ];
    }

    get tooltipLabel() {
        return this.props.record.fields[this.props.name].string;
    }
    get options() {
        return Array.from(this.props.record.fields[this.props.name].selection);
    }
    get index() {
        return this.state.index > -1
            ? this.state.index
            : this.options.findIndex((o) => o[0] === this.props.record.data[this.props.name]);
    }

    getTooltip(value) {
        return this.tooltipLabel && this.tooltipLabel !== value
            ? `${this.tooltipLabel}: ${value}`
            : value;
    }
    /**
     * @param {string} value
     */
    onStarClicked(value) {
        if (this.props.record.data[this.props.name] === value) {
            this.state.index = -1;
            this.updateRecord(this.options[0][0]);
        } else {
            this.updateRecord(value);
        }
    }

    async updateRecord(value) {
        await this.props.record.update({ [this.props.name]: value }, { save: this.props.autosave });
    }
}

export const priorityField = {
    component: PriorityField,
    displayName: _t("Priority"),
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
    ],
    supportedTypes: ["selection"],
    extractProps({ options, viewType }, dynamicInfo) {
        return {
            withCommand: viewType === "form",
            readonly: dynamicInfo.readonly,
            autosave: "autosave" in options ? !!options.autosave : true,
        };
    },
};

registry.category("fields").add("priority", priorityField);
