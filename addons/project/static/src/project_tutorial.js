import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("web_tutorial.tutorials").add("project_tutorial", [
    {
        model: "project.project",
        steps: [
            {
                action: "click",
                content: _t("Start a new project to organize your work."),
                trigger: ".o_control_panel .o-kanban-button-new",
                type: "action",
            },
        ],
        viewType: "kanban",
    },
    {
        model: "project.project",
        steps: [
            {
                content: _t("Give your project a name, e.g. Office move or Website redesign."),
                name: "name",
                type: "field",
            },
            {
                action: "click",
                content: _t("All set! Create your project and jump into its tasks."),
                trigger: "button[name='action_view_tasks']",
                type: "action",
            },
        ],
        viewType: "form",
    },
    {
        model: "project.task",
        steps: [
            {
                action: "click",
                content: _t(
                    "Name the first stage your tasks will go through, e.g. To Do, then add it."
                ),
                trigger: ".o_quick_create_unfolded .o_kanban_add",
                type: "action",
            },
            {
                action: "click",
                content: _t("Now, create your first task."),
                trigger:
                    ".o_control_panel .o-kanban-button-new, .o_kanban_group .o_kanban_quick_add",
                type: "action",
            },
            {
                content: _t("What needs to be done? Describe the task in a few words."),
                name: "display_name",
                type: "field",
            },
            {
                content: _t("Who's on it? Assign the task to yourself or a teammate."),
                name: "user_ids",
                type: "field",
            },
            {
                action: "click",
                content: _t("Open the task to add more details."),
                trigger: ".o_kanban_quick_create .o_kanban_edit",
                type: "action",
            },
        ],
        viewType: "kanban",
    },
    {
        model: "project.task",
        steps: [
            {
                content: _t("Is it urgent? Star it so it stands out."),
                name: "priority",
                type: "field",
            },
            {
                content: _t("Add tags to find similar tasks at a glance (e.g. Design, Bug)."),
                name: "tag_ids",
                type: "field",
            },
            {
                content: _t("When should it be done? Set a deadline."),
                name: "date_deadline",
                type: "field",
            },
            {
                content: _t("Write down the details, so everyone knows what to do."),
                name: "description",
                type: "field",
            },
            {
                action: "click",
                content: _t(
                    "Send a message to the followers of the task: they receive it by email."
                ),
                trigger: ".o-mail-Chatter-sendMessage",
                type: "action",
            },
            {
                action: "click",
                content: _t("Log an internal note: only your colleagues will see it."),
                trigger: ".o-mail-Chatter-logNote",
                type: "action",
            },
            {
                content: _t("Making progress? Move the task to the next stage."),
                name: "stage_id",
                type: "field",
            },
        ],
        viewType: "form",
    },
]);
