import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import "@website_sale/website_builder/website_sale_form_editor";

const requestWithdrawalFormInfo = registry
    .category("builder.form_editor_actions")
    .get("request_withdrawal");

registry.category("builder.form_editor_actions").add("request_withdrawal", {
    ...requestWithdrawalFormInfo,
    fields: [
        ...requestWithdrawalFormInfo.fields,
        {
            name: "project_id",
            type: "many2one",
            relation: "project.project",
            string: _t("Project"),
            domain: [["is_template", "=", false]],
            createAction: "project.open_view_project_all",
        },
    ],
}, { force: true });
