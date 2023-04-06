/** @odoo-module */

import {
    StateSelectionField,
    stateSelectionField,
} from "@web/views/fields/state_selection/state_selection_field";
import { sprintf } from "@web/core/utils/strings";
import { useCommand } from "@web/core/commands/command_hook";
import { formatSelection } from "@web/views/fields/formatters";

import { registry } from "@web/core/registry";

const { useState } = owl;

export class ProjectTaskStateSelection extends StateSelectionField {
    setup() {
        this.state = useState({
            isStateButtonHighlighted: false,
        });
        this.icons = {
            "01_in_progress": "o_status",
            "03_approved": "o_status o_status_green",
            "02_changes_requested": "fa fa-lg fa-exclamation-circle",
            "1_done": "fa fa-lg fa-check-circle",
            "1_canceled": "fa fa-lg fa-times-circle",
            "04_waiting_normal": "fa fa-lg fa-hourglass-o",
        };
        this.colorIcons = {
            "01_in_progress": "",
            "03_approved": "text-success",
            "02_changes_requested": "o_status_changes_requested",
            "1_done": "text-success",
            "1_canceled": "text-danger",
            "04_waiting_normal": "",
        };
        this.colorButton = {
            "01_in_progress": "btn-outline-secondary",
            "03_approved": "btn-outline-success",
            "02_changes_requested": "btn-outline-warning",
            "1_done": "btn-outline-success",
            "1_canceled": "btn-outline-danger",
            "04_waiting_normal": "btn-outline-secondary",
        };
        if (this.props.viewType != 'form') {
            super.setup();
        } else {
            const commandName = sprintf(this.env._t(`Set state as...`));
            useCommand(
                commandName,
                () => {
                    return {
                        placeholder: commandName,
                        providers: [
                            {
                                provide: () =>
                                    this.options.map(subarr => ({
                                        name: subarr[1],
                                        action: () => {
                                            this.updateRecord(subarr[0]);
                                        },
                                    })),
                            },
                        ],
                    };
                },
                {
                    category: "smart_action",
                    hotkey: "alt+f",
                    isAvailable: () => !this.props.readonly && !this.props.isDisabled,
                }
            );
        }
    }

    get options() {
        const options = [
            ["1_canceled", this.env._t("Canceled")],
            ["1_done", this.env._t("Done")],
        ];
        if (this.currentValue != "04_waiting_normal") {
            return [
                ["01_in_progress", this.env._t("In Progress")],
                ["02_changes_requested", this.env._t("Changes Requested")],
                ["03_approved", this.env._t("Approved")],
                ...options,
            ];
        }
        return options;
    }

    get availableOptions() {
        // overrided because we need the currentOption in the dropdown as well
        return this.options;
    }

    get label() {
        const fullSelection = [...this.options];
        fullSelection.push(["04_waiting_normal", "Waiting"]);
        return formatSelection(this.currentValue, {
            selection: fullSelection,
        });
    }

    stateIcon(value) {
        return this.icons[value] || "";
    }

    /**
     * @override
     */
    statusColor(value) {
        return this.colorIcons[value] || "";
    }

    /**
     * determine if a single click will trigger the toggleState() method
     * which will switch the state from in progress to done.
     * Either the isToggleMode is active on the record OR the task is_private
     */
    get isToggleMode() {
        return this.props.isToggleMode || !this.props.record.data.project_id;
    }

    isView(viewNames) {
        return viewNames.includes(this.props.viewType);
    }

    async toggleState() {
        const toggleVal = this.currentValue == "1_done" ? "01_in_progress" : "1_done";
        await this.updateRecord(toggleVal);
    }

    getDropdownPosition() {
        if (this.isView(['kanban', 'list', 'calendar']) || this.env.isSmall) {
            return '';
        }
        return 'bottom-end';
    }

    getTogglerClass(currentValue) {
        if (this.isView(['kanban', 'list', 'calendar']) || this.env.isSmall) {
            return 'btn btn-link d-flex p-0';
        }
        return 'o_state_button btn rounded-pill ' + this.colorButton[currentValue];
    }

    async updateRecord(value) {
        const result = await super.updateRecord(value);
        this.state.isStateButtonHighlighted = false;
        if (result) {
            return result;
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onMouseEnterStateButton(ev) {
        if (!this.env.isSmall) {
            this.state.isStateButtonHighlighted = true;
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onMouseLeaveStateButton(ev) {
        this.state.isStateButtonHighlighted = false;
    }
}

ProjectTaskStateSelection.template = "project.ProjectTaskStateSelection";

ProjectTaskStateSelection.props = {
    ...stateSelectionField.component.props,
    isToggleMode: { type: Boolean, optional: true },
    viewType: { type: String },
}


export const projectTaskStateSelection = {
    ...stateSelectionField,
    component: ProjectTaskStateSelection,
    fieldDependencies: [{ name: "project_id", type: "many2one" }],
    extractProps({ options, viewType }) {
        const props = stateSelectionField.extractProps(...arguments);
        props.isToggleMode = Boolean(options.is_toggle_mode);
        props.viewType = viewType;
        return props;
    },
}

registry.category("fields").add("project_task_state_selection", projectTaskStateSelection);
