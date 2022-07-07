/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";

const { Component, useState } = owl;

export class PriorityField extends Component {
    setup() {
        this.state = useState({
            index: -1,
        });
        if (this.props.record.activeFields[this.props.name].viewType === "form") {
            this.initiateCommand();
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
            this.props.update(this.options[0][0]);
        } else {
            this.props.update(value);
        }
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
            const name = this.env._t("Set priority...");
            const action = () => {
                return commandService.openPalette({
                    placeholder: this.env._t("Set a priority..."),
                    providers: [{ provide }],
                });
            };
            const options = {
                category: "smart_action",
                hotkey: "alt+r",
            };
            commandService.add(name, action, options);
        } catch {
            console.log("Could not add command to service");
        }
    }
}

PriorityField.template = "web.PriorityField";
PriorityField.props = {
    ...standardFieldProps,
    tooltipLabel: { type: String, optional: true },
};

PriorityField.displayName = _lt("Priority");
PriorityField.supportedTypes = ["selection"];

PriorityField.extractProps = ({ field }) => {
    return {
        tooltipLabel: field.string,
    };
};

registry.category("fields").add("priority", PriorityField);
