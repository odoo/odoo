// TODO Delete me when moving to website ! This is about checking that other modules can work too.
// This is a copy of website_sale_form_editor.js which cannot be accessed from this module.
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("website.form_editor_actions").add("create_customer", {
    formFields: [
        {
            type: "char",
            modelRequired: true,
            name: "name",
            fillWith: "name",
            string: _t("Your Name"),
        },
        {
            type: "email",
            required: true,
            fillWith: "email",
            name: "email",
            string: _t("Your Email"),
        },
        {
            type: "tel",
            fillWith: "phone",
            name: "phone",
            string: _t("Phone Number"),
        },
        {
            type: "char",
            name: "company_name",
            fillWith: "commercial_company_name",
            string: _t("Company Name"),
        },
    ],
    fields: [
        {
            name: "author_id",
            type: "many2one",
            relation: "res.users",
            domain: [],
            string: _t("Author"),
            title: _t("Author."),
        },
    ],
});
