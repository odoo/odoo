import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

// This is translated into the user language as it is used in the builder sidebar
registry.category("builder.form_editor_actions").add("send_mail", {
    fields: [
        {
            name: "email_to",
            type: "char",
            required: true,
            string: _t("Recipient Emails"),
            defaultValue: "info@yourcompany.example.com",
            help: _t("Add multiple emails separated by commas"),
        },
    ],
});
