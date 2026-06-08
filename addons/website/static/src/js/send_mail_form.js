import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { getParsedDataFor } from "@website/js/utils";

/**
 * Return the default recipient email used when a form has no explicit recipient.
 * Prefer the current website company's email, then fallback to the current user's email.
 *
 * @returns {Promise<string>}
 */
export async function getDefaultEmailTo({ services }) {
    const companyId = services.website?.currentWebsite?.company_id;
    let defaultEmailTo;
    if (companyId) {
        const companies = await services.orm.cache().read("res.company", [companyId], ["email"]);
        defaultEmailTo = companies[0].email;
    }
    if (!defaultEmailTo && user.userId) {
        const users = await services.orm.cache().read("res.users", [user.userId], ["email"]);
        defaultEmailTo = users[0].email;
    }
    return defaultEmailTo || "";
}

async function applyDefaultEmailTo({ formEl, services }) {
    if (formEl.dataset.model_name !== "mail.mail") {
        return;
    }
    const emailToInputEl = formEl.querySelector(`.s_website_form_dnone input[name="email_to"]`);
    if (
        emailToInputEl &&
        !emailToInputEl.value &&
        !getParsedDataFor(formEl.id, formEl.ownerDocument)?.["email_to"]
    ) {
        emailToInputEl.setAttribute("value", await getDefaultEmailTo({ services }));
    }
}

// This is translated into the user language as it is used in the builder sidebar
registry.category("builder.form_editor_actions").add("send_mail", {
    fields: [
        {
            name: "email_to",
            type: "char",
            required: true,
            string: _t("Recipient Emails"),
            getDefaultValue: getDefaultEmailTo,
            applyDefaultValue: applyDefaultEmailTo,
            help: _t("Add multiple emails separated by commas"),
        },
    ],
});
