import { useState } from "@web/owl2/utils";
import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { ProjectTemplateButtons } from "./project_template_buttons";

export class ProjectTaskTemplateDropdown extends Component {
    static template = "project.TemplateDropdown";
    static components = {
        Dropdown,
        DropdownItem,
        ProjectTemplateButtons,
    };

    static props = {
        archInfo: {
            type: Object,
            optional: true,
        },
        hotkey: {
            type: String,
            optional: true,
        },
        newButtonClasses: String,
        onCreate: Function,
        // Can be a number, false (in to-do) or undefined
        projectId: {
            type: [Number, Boolean],
            optional: true,
        },
        context: Object,
        getAdditionalContext: {
            type: Function,
            optional: true,
        },
    };
    static defaultProps = {
        hotkey: "c",
        projectId: null,
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.offlineService = useService("offline");
        this.state = useState({ taskTemplates: [] });
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        if (this.props.projectId) {
            this.state.taskTemplates = await this.orm
                .cache({
                    type: "disk",
                    update: "always",
                    callback: (result, hasChanged) => {
                        if (hasChanged) {
                            this.state.taskTemplates = result;
                        }
                    },
                })
                .call("project.project", "get_template_tasks", [this.props.projectId]);
        }
    }
    
    get isNewButtonAvailableOffline() {
        const { actionId, viewType } = this.env.config;
        if (viewType === "list") {
            return !this.props.archInfo.editable && this.offlineService.isAvailableOffline(actionId, "form", false);
        } else if (viewType === "kanban" ) {
            if (this.props.archInfo.activeActions.quickCreate) {
            return this.offlineService.isAvailableOffline(actionId, "kanban_quick_create", false);
            }
            return this.offlineService.isAvailableOffline(actionId, "form", false);
        } else if (viewType === "form") {
            return this.offlineService.isAvailableOffline(actionId, "form", false);
        }
        return false;
    }

    async createTaskFromTemplate(templateId) {
        const context = { ...this.props.context };
        if (this.props.getAdditionalContext) {
            Object.assign(context, this.props.getAdditionalContext());
        }
        this.action.switchView("form", {
            resId: await this.orm.call(
                "project.task",
                "action_create_from_template",
                [templateId],
                {
                    context: context,
                }
            ),
            focusTitle: true,
        });
    }
}
