import { Component, onWillStart, props, proxy, t } from "@odoo/owl";
import { useService, useOwnedDialogs } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { user } from "@web/core/user";

import { ProjectTemplateButtons } from "./project_template_buttons";

export class ProjectTaskTemplateDropdown extends Component {
    static template = "project.TemplateDropdown";
    static components = {
        Dropdown,
        DropdownItem,
        ProjectTemplateButtons,
    };

    props = props({
        archInfo: t.object().optional(),
        hotkey: t.string().optional("c"),
        newButtonClasses: t.string(),
        onCreate: t.function(),
        // Can be a number, false (in to-do) or undefined
        projectId: t.or([t.number(), t.boolean()]).optional(false),
        context: t.object(),
        getAdditionalContext: t.function().optional(),
    });

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.offlineService = useService("offline");
        this.addDialog = useOwnedDialogs();
        this.displayTasksLimit = 10;
        this.state = proxy({ taskTemplates: [] });
        this.isProjectManager = false;
        onWillStart(this.onWillStart);
    }

    get displayViewMoreButton() {
        return this.state.taskTemplates.length > this.displayTasksLimit;
    }

    get displayedtaskTemplates() {
        return this.state.taskTemplates.slice(0, this.displayTasksLimit);
    }

    get taskTemplateButtonClasses() {
        let classes = 'btn btn-link o-dropdopwn-item-indent o-task-template d-flex align-items-center';
        if (this.isProjectManager) {
            classes += ' pe-0';
        }
        return classes;
    }

    async onWillStart() {
        if (this.props.projectId) {
            await Promise.all([
                    user.hasGroup("project.group_project_manager").then((res) => (this.isProjectManager = res)),
                    this._fetchTasktemplates(),
                ]);
        }
    }

    get isNewButtonAvailableOffline() {
        const { actionId, viewType } = this.env.config;
        if (viewType === "list") {
            return (
                !this.props.archInfo.editable &&
                this.offlineService.isAvailableOffline(actionId, "form", false)
            );
        } else if (viewType === "kanban") {
            if (this.props.archInfo.activeActions.quickCreate) {
                return this.offlineService.isAvailableOffline(
                    actionId,
                    "kanban_quick_create",
                    false
                );
            }
            return this.offlineService.isAvailableOffline(actionId, "form", false);
        } else if (viewType === "form") {
            return this.offlineService.isAvailableOffline(actionId, "form", false);
        }
        return false;
    }

    async _fetchTasktemplates() {
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
