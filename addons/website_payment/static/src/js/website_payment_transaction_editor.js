import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("website.form_editor_actions").add("donation_form", {
    formFields: [{
        name: "name",
        modelRequired: true,
        fillWith: "name",
        string: _t("Name"),
        type: "char",
    }, {
        name: "email",
        modelRequired: true,
        fillWith: "email",
        string: _t("Email"),
        type: "email",
    }, {
        name: "country_id",
        relation: "res.country",
        modelRequired: true,
        string: _t("Country"),
        type: "many2one",
    }],
});
