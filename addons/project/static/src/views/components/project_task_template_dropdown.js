import { Component, onWillStart, useState } from "@odoo/owl";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";

import { ProjectTemplateButtons } from "./project_template_buttons";

export class ProjectTaskTemplateDropdown extends Component {
    static template = "project.TemplateDropdown";
    static components = {
        Dropdown,
        DropdownItem,
        ProjectTemplateButtons,
    };

    static props = {
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
        this.addDialog = useOwnedDialogs();
        this.displayTasksLimit = 10;
        this.state = useState({ taskTemplates: [] });
        onWillStart(this.onWillStart);
    }

    get displayViewMoreButton() {
        return this.state.taskTemplates.length > this.displayTasksLimit;
    }

    get displayedtaskTemplates() {
        return this.state.taskTemplates.slice(0, this.displayTasksLimit);
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

    onClickViewMore() {
        this.addDialog(SelectCreateDialog, {
            title: _t("Tasks Templates"),
            noCreate: true,
            multiSelect: false,
            resModel: "project.task",
            context: {
                list_view_ref: "project.project_task_view_tree_base",
            },
            domain: [
                ["project_id", "in", [this.props.projectId, false]],
                ["is_template", "=", true],
            ],
            onSelected: ([taskTemplateId]) => {
                this.createTaskFromTemplate(taskTemplateId);
            },
        });
    }
}
