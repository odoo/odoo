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
            createAction: "project.open_view_project_all",
        },
    ],
    successPage: "/your-task-has-been-submitted",
});
