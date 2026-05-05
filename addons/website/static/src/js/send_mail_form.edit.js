import { _t, translationIsReady } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

// translations need to be loaded to avoid TranslatedString in templates
translationIsReady.then(() => {
    registry.category("website.form_editor_actions").add("send_mail", {
        formFields: [
            {
                type: "char",
                custom: true,
                required: true,
                fillWith: "name",
                name: "name",
                string: _t("Your Name"),
            },
            {
                type: "tel",
                custom: true,
                fillWith: "phone",
                name: "phone",
                string: _t("Phone Number"),
            },
            {
                type: "email",
                modelRequired: true,
                fillWith: "email",
                name: "email_from",
                string: _t("Your Email"),
            },
            {
                type: "char",
                custom: true,
                fillWith: "parent_name",
                name: "company",
                string: _t("Your Company"),
            },
            {
                type: "char",
                modelRequired: true,
                name: "subject",
                string: _t("Subject"),
            },
            {
                type: "text",
                custom: true,
                required: true,
                name: "description",
                string: _t("Your Question"),
            },
        ],
    });
});
