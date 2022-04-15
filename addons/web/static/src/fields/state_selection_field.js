/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

export class StateSelectionField extends Component {
    setup() {
        this.initiateCommand(); //TODO only if view === form
    }
    get colorClass() {
        if (this.currentValue === "blocked") {
            return "o_status_red";
        } else if (this.currentValue === "done") {
            return "o_status_green";
        }
        return "";
    }
    get currentValue() {
        return this.props.value || this.props.options[0][0];
    }
    get label() {
        return this.props.options.find((o) => o[0] === this.currentValue)[1];
    }

    initiateCommand() {
        try {
            const commandService = useService("command");
            const provide = () => {
                return this.props.options.map((value) => ({
                    name: value[1],
                    action: () => {
                        this.props.update(value[0]);
                    },
                }));
            };
            const name = this.env._t("Set kanban state...");
            const action = () => {
                return commandService.openPalette({
                    placeholder: this.env._t("Set a kanban state..."),
                    providers: [{ provide }],
                });
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
    /**
     * @param {Event} ev
     */
    onChange(value) {
        this.props.update(value);
    }
}

StateSelectionField.template = "web.StateSelectionField";
StateSelectionField.components = {
    Dropdown,
    DropdownItem,
};
StateSelectionField.defaultProps = {
    hideLabel: false,
};
StateSelectionField.props = {
    ...standardFieldProps,
    hideLabel: { type: Boolean, optional: true },
    options: Object,
};
StateSelectionField.displayName = _lt("Label Selection");
StateSelectionField.supportedTypes = ["selection"];
StateSelectionField.extractProps = (fieldName, record, attrs) => {
    return {
        hideLabel: attrs.options.hide_label,
        options: record.fields[fieldName].selection,
        readonly: record.isReadonly(fieldName),
    };
};
registry.category("fields").add("state_selection", StateSelectionField);
registry.category("fields").add("list.state_selection", StateSelectionField); // WOWL: because it exists in legacy
