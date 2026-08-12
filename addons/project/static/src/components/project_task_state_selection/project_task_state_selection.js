import { useProps, proxy, t } from "@odoo/owl";
import { useCommand } from "@web/core/commands/command_hook";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatSelection } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {
    StateSelectionField,
    stateSelectionField,
} from "@web/views/fields/state_selection/state_selection_field";

export class ProjectTaskStateSelection extends StateSelectionField {
    static template = "project.ProjectTaskStateSelection";

    props = useProps({
        ...standardFieldProps,
        showLabel: t.boolean().optional(true),
        withCommand: t.boolean().optional(),
        isToggleMode: t.boolean().optional(),
        viewType: t.string().optional(),
    });

    setup() {
        this.uiService = useService("ui");
        this.state = proxy({
            isStateButtonHighlighted: false,
        });
        this.icons = {
            "02_changes_requested": "circle",
            "1_done": "check_circle",
            "1_canceled": "cancel",
            "04_waiting_normal": "hourglass_empty",
            "01_in_progress": "circle",
            "03_approved": "circle",
        };
        this.classIcons = {
            "1_done": "oi-filled",
            "1_canceled": "oi-filled",
            "02_changes_requested": "oi-filled",
            "03_approved": "oi-filled",
        };
        this.colorIcons = {
            "01_in_progress": "text-muted",
            "03_approved": "o_status o_status_green",
            "02_changes_requested": "o_status o_status_orange",
            "1_done": "o_status o_status_green",
            "1_canceled": "o_status o_status_red",
            "04_waiting_normal": "o_status o_status_blue",
        };
        if (this.props.viewType != 'form') {
            super.setup();
        } else {
            const commandName = _t("Set state as...");
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
        const labels = new Map(super.options);
        const states = ["1_canceled", "1_done"];
        const currentState = this.props.record.data[this.props.name];
        if (currentState != "04_waiting_normal") {
            states.unshift("01_in_progress", "02_changes_requested", "03_approved");
        }
        return states.map((state) => [state, labels.get(state)]);
    }

    get availableOptions() {
        // overrided because we need the currentOption in the dropdown as well
        return this.options;
    }

    get label() {
        const waitOption = super.options.findLast(([state, _]) => state === "04_waiting_normal");
        const fullSelection = [...this.options, waitOption];
        return formatSelection(this.currentValue, {
            selection: fullSelection,
        });
    }

    /**
     * @override
     */
    stateIcon(value) {
        return this.icons[value] || "";
    }

    /**
     * @override
     */
    stateIconClass(value) {
        return this.classIcons[value] || "";
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

    // The tooltip service copies data-tooltip when the mouse enters and never re-reads it.
    // So we can't switch the text on isStateButtonHighlighted (set on that same mouseenter):
    // the open tooltip would keep the old label. Return the hovered text ("Mark as done") directly.
    get toggleTooltip() {
        if (this.props.showLabel) {
            return "";
        }
        return this.uiService.isSmall ? this.label : _t("Mark as done");
    }

    async toggleState() {
        const toggleVal = this.currentValue == "1_done" ? "01_in_progress" : "1_done";
        await this.updateRecord(toggleVal);
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
        if (!this.uiService.isSmall) {
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

export const projectTaskStateSelection = {
    ...stateSelectionField,
    component: ProjectTaskStateSelection,
    fieldDependencies: [{ name: "project_id", type: "many2one" }],
    supportedOptions: [
        ...stateSelectionField.supportedOptions, {
            label: _t("Is toggle mode"),
            name: "is_toggle_mode",
            type: "boolean"
        }
    ],
    extractProps({ options }) {
        const props = stateSelectionField.extractProps(...arguments);
        props.isToggleMode = Boolean(options.is_toggle_mode);
        return props;
    },
}

registry.category("fields").add("project_task_state_selection", projectTaskStateSelection);
