/** @odoo-module **/

import { useCommand } from "@web/core/commands/command_hook";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

import { Component, useState } from "@odoo/owl";

export class PriorityField extends Component {
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
                                            this.props.update(value[0]);
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

    get options() {
        return Array.from(this.props.record.fields[this.props.name].selection);
    }
    get index() {
        return this.state.index > -1
            ? this.state.index
            : this.options.findIndex((o) => o[0] === this.props.value);
    }
    get isReadonly() {
        return this.props.record.isReadonly(this.props.name);
    }

    getTooltip(value) {
        return this.props.tooltipLabel ? `${this.props.tooltipLabel}: ${value}` : value;
    }
    /**
     * @param {string} value
     */
    onStarClicked(value) {
        if (this.props.value === value) {
            this.state.index = -1;
            this.props.update(this.options[0][0], { save: this.props.autosave });
        } else {
            this.props.update(value, { save: this.props.autosave });
        }
    }
}

PriorityField.template = "web.PriorityField";
PriorityField.props = {
    ...standardFieldProps,
    tooltipLabel: { type: String, optional: true },
    autosave: { type: Boolean, optional: true },
};

PriorityField.displayName = _lt("Priority");
PriorityField.supportedTypes = ["selection"];

PriorityField.extractProps = ({ field, attrs }) => {
    return {
        tooltipLabel: field.string,
        autosave: "autosave" in attrs.options ? !!attrs.options.autosave : true,
    };
};

registry.category("fields").add("priority", PriorityField);
