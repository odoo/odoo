import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { patch } from "@web/core/utils/patch";
import { IrModel } from "@web/../tests/_framework/mock_server/mock_models/ir_model";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { animationFrame } from "@odoo/hoot-dom";

class HrJob extends models.Model {
    _name = "hr.job";
}
defineModels([HrJob]);

patch(IrModel.prototype, {
    get_compatible_form_models() {
        return [
            {
                id: 687,
                model: "hr.applicant",
                name: "Applicant",
                website_form_label: "Apply for a Job",
                website_form_key: "apply_job",
            },
            {
                id: 85,
                model: "res.partner",
                name: "Contact",
                website_form_label: "Create a Customer",
                website_form_key: "create_customer",
            },
            {
                id: 184,
                model: "mail.mail",
                name: "Outgoing Mails",
                website_form_label: "Send an E-mail",
                website_form_key: "send_mail",
            },
        ];
    },
});

defineWebsiteModels();

test("change action of form changes available options", async () => {
    // reduced version of form_editor_actions
    registry
        .category("website.form_editor_actions")
        .add("apply_job", {
            formFields: [
                { type: "char", name: "partner_name", fillWith: "name", string: _t("Your Name") },
            ],
            fields: [
                { name: "job_id", type: "many2one", relation: "hr.job", string: _t("Applied Job") },
            ],
            successPage: "/job-thank-you",
        })
        .add("create_customer", {
            formFields: [{ type: "char", name: "name", fillWith: "name", string: _t("Your Name") }],
        });

    await setupWebsiteBuilder(
        `<section class="s_website_form"><form data-model_name="mail.mail">
            <div class="s_website_form_field"><label class="s_website_form_label" for="contact1">Name</label><input id="contact1" class="s_website_form_input"/></div>
            <div class="s_website_form_submit">
                <div class="s_website_form_label"/>
                <a>Submit</a>
            </div>
        </form></section>`
    );

    await contains(":iframe section").click();
    await contains("div:has(>span:contains('Action')) + div button").click();
    await contains("div.o-dropdown-item:contains('Apply for a Job')").click();

    await animationFrame();
    expect("span:contains('Applied Job')").toHaveCount(1);
    expect("div:has(>span:contains('URL')) + div input").toHaveValue("/job-thank-you");

    await contains("div:has(>span:contains('Action')) + div button").click();
    await contains("div.o-dropdown-item:contains('Create a Customer')").click();

    expect("span:contains('Applied Job')").toHaveCount(0);
    expect("div:has(>span:contains('URL')) + div input").toHaveValue("/contactus-thank-you");
});
