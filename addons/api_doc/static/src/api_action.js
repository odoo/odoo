import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("actions").add("doc_api_key_wizard", () => {
    return {
        type: "ir.actions.act_window",
        name: _t("API Key Wizard"),
        res_model: "res.users.apikeys.description",
        views: [[false, "form"]],
        target: "new",
    }
});
