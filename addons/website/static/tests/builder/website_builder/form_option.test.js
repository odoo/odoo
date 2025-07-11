import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
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

test("undo redo add form field", async () => {
    onRpc("get_authorized_fields", () => ({}));
    const { getEditor } = await setupWebsiteBuilder(
        `<section class="s_website_form"><form data-model_name="mail.mail">
            <div class="s_website_form_field"><label class="s_website_form_label" for="contact1">Name</label><input id="contact1" class="s_website_form_input"/></div>
            <div class="s_website_form_submit">
                <div class="s_website_form_label"/>
                <a>Submit</a>
            </div>
        </form></section>`
    );
    const editor = getEditor();

    await contains(":iframe section").click();
    await contains("button[title='Add a new field at the end']").click();

    expect(":iframe span.s_website_form_label_content").toHaveCount(1);
    undo(editor);
    redo(editor);
    expect(":iframe span.s_website_form_label_content").toHaveCount(1);

    await contains(":iframe span.s_website_form_label_content").click();
    await contains("button[title='Add a new field after this one']").click();

    expect(":iframe span.s_website_form_label_content").toHaveCount(2);
    undo(editor);
    undo(editor);
    expect(":iframe span.s_website_form_label_content").toHaveCount(0);
});

test("empty placeholder selection input for selection field", async () => {
    onRpc("get_authorized_fields", () => ({}));
    const { getEditor } = await setupWebsiteBuilder(
        `<section class="s_website_form"><form data-model_name="mail.mail">
            <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom" data-type="many2one">
                <div class="row s_col_no_resize s_col_no_bgcolor">
                    <label class="col-form-label col-sm-auto s_website_form_label" for="ozp7022vqhe">
                        <span class="s_website_form_label_content">Selection Field</span>
                    </label>
                    <div class="col-sm">
                        <select class="form-select s_website_form_input" name="Phone Number" id="ozp7022vqhe">
                            <option id="ozp7022vqhe0" value="Option 1">Option 1</option>
                            <option id="ozp7022vqhe1" value="Option 2">Option 2</option>
                            <option id="ozp7022vqhe2" value="Option 3">Option 3</option>
                        </select>
                    </div>
                </div>
            </div>
            <div class="s_website_form_submit">
                <div class="s_website_form_label"/>
                <a>Submit</a>
            </div>
        </form></section>`
    );
    getEditor();
    expect(":iframe select option").toHaveCount(3);
    await contains(":iframe .s_website_form_field[data-type='many2one'").click();
    await contains(".o_we_table_wrapper input[type='checkbox']").click();
    expect(":iframe select option").toHaveCount(4);
    expect(":iframe select option:eq(0)").toHaveText("");
});
