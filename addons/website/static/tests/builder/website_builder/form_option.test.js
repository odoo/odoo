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

test("field's name stays after modifying the options list", async () => {
    onRpc("get_authorized_fields", () => ({}));
    await setupWebsiteBuilder(
        `<section class="s_website_form pt16 pb16 o_colored_level" data-vcss="001" data-snippet="s_website_form" data-name="Form">
            <div class="container-fluid">
            <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" 
                data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you" contenteditable="false">
                <div class="s_website_form_rows row s_col_no_bgcolor">
                    <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_required" data-type="many2one">
                        <div class="row s_col_no_resize s_col_no_bgcolor">
                            <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oyeqnysxh10b">
                                <span class="s_website_form_label_content">Author</span>
                            </label>
                            <div class="col-sm">
                                <select class="form-select s_website_form_input" required="" id="oyeqnysxh10b" name="author_id" />
                            </div>
                        </div>
                    </div>
                </div>
            </form>
            </div>
        </section>`
    );

    expect(":iframe section select.s_website_form_input").toHaveAttribute("name", "author_id");
    await contains(":iframe section span:contains(Author)").click();
    await contains("button.builder_list_add_item").click();
    expect(":iframe section select.s_website_form_input").toHaveAttribute("name", "author_id");
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
