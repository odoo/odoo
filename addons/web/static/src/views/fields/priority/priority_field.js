/** @odoo-module **/

import { useCommand } from "@web/core/commands/command_hook";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { evalDomain } from "@web/views/utils";
import { Component, useState } from "@odoo/owl";

export class PriorityField extends Component {
    static template = "web.PriorityField";
    static props = {
        ...standardFieldProps,
        readonlyFromModifiers: { type: Array | Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            index: -1,
        });
        if (this.props.record.activeFields[this.props.name].viewType === "form") {
            const commandName = this.env._t("Set priority...");
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
                                            this.updateRecord(value[0]);
                                        },
                                    })),
                            },
                        ],
                    };
                },
                { category: "smart_action", hotkey: "alt+r" }
            );
        }
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
            : this.options.findIndex((o) => o[0] === this.props.value);
    }
    get isReadonly() {
        return evalDomain(this.props.readonlyFromModifiers, this.props.record.evalContext) || false;
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
        if (this.props.value === value) {
            this.state.index = -1;
            this.updateRecord(this.options[0][0]);
        } else {
            this.updateRecord(value);
        }
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

export const priorityField = {
    component: PriorityField,
    displayName: _lt("Priority"),
    supportedTypes: ["selection"],
    extractProps: ({ modifiers }) => ({
        readonlyFromModifiers: modifiers.readonly,
    }),
};

registry.category("fields").add("priority", priorityField);
