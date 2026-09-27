import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getDefaultEmailTo } from "@website/js/send_mail_form";
import { getParsedDataFor } from "@website/js/utils";

/**
 * Return the default recipient emails for the withdrawal request notification.
 * Prefer the current website's salesperson email, then fallback to the
 * current website company's email (or the editor user's email).
 *
 * @returns {Promise<string>}
 */
async function getDefaultRecipientEmails({ services }) {
    const websiteId = services.website?.currentWebsite?.id;
    if (websiteId) {
        try {
            const [website] = await services.orm.webRead("website", [websiteId], {
                specification: { salesperson_id: { fields: { email: {} } } },
            });
            if (website.salesperson_id?.email) {
                return website.salesperson_id.email;
            }
        } catch {
            // In cross-company editing, the editor user may not have access to
            // the website's salesperson: fall back to the company/user email below.
        }
    }
    return getDefaultEmailTo({ services });
}

async function applyDefaultRecipientEmails({ formEl, services }) {
    const recipientEmailsInputEl = formEl.querySelector(
        `.s_website_form_dnone input[name="recipient_emails"]`
    );
    if (
        recipientEmailsInputEl &&
        !recipientEmailsInputEl.value &&
        !getParsedDataFor(formEl.id, formEl.ownerDocument)?.["recipient_emails"]
    ) {
        recipientEmailsInputEl.setAttribute(
            "value",
            await getDefaultRecipientEmails({ services })
        );
    }
}

registry.category("builder.form_editor_actions").add("request_withdrawal", {
    fields: [
        {
            name: "recipient_emails",
            type: "char",
            required: false,
            string: _t("Recipient Emails"),
            help: _t("Email addresses of the recipients of the withdrawal request notification"),
            getDefaultValue: getDefaultRecipientEmails,
            applyDefaultValue: applyDefaultRecipientEmails,
        },
    ],
});
