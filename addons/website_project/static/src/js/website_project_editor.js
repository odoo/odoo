import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("builder.form_editor_actions").add("create_task", {
    fields: [
        {
            name: "project_id",
            type: "many2one",
            required: true,
            relation: "project.project",
            string: _t("Project"),
            domain: [["is_template", "=", false]],
            dialogTitle: _t("Create a Project"),
            dialogDescription: _t(
                "Your current changes will be saved, and you'll be redirected to the Project app."
            ),
            noRecordMessage: _t("To create a task, you must first create a project."),
            createAction: "project.open_view_project_all",
        },
    ],
    successPage: "/your-task-has-been-submitted",
});
