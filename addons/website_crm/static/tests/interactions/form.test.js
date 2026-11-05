import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.form");
describe.current.tags("interaction_dev");

function getContactForm(modelName, fieldNames) {
    return `
        <span class="hidden" data-for="contactus_form" data-values="{'name': '', 'subject': 'Office Desk'}"/>
        <section class="s_website_form" data-snippet="s_website_form">
            <form id="contactus_form" action="/website/form/" method="post" data-model_name="${modelName}">
                ${fieldNames
                    .map(
                        (name) =>
                            `<input type="text" class="form-control s_website_form_input" name="${name}"/>`
                    )
                    .join("")}
            </form>
        </section>
    `;
}

test("lead form uses the subject value as lead name", async () => {
    await startInteractions(getContactForm("crm.lead", ["name"]));
    expect(queryOne("form input[name=name]")).toHaveValue("Office Desk");
});

test("email form uses the subject value as subject only", async () => {
    await startInteractions(getContactForm("mail.mail", ["name", "subject"]));
    expect(queryOne("form input[name=subject]")).toHaveValue("Office Desk");
    expect(queryOne("form input[name=name]")).toHaveValue("");
});
