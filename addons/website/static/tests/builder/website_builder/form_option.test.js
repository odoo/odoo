import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "../website_helpers";
import { patch } from "@web/core/utils/patch";
import { IrModel } from "@web/../tests/_framework/mock_server/mock_models/ir_model";
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
                { type: "char", name: "partner_name", fillWith: "name", string: "Your Name" },
            ],
            fields: [
                { name: "job_id", type: "many2one", relation: "hr.job", string: "Applied Job" },
            ],
            successPage: "/job-thank-you",
        })
        .add("create_customer", {
            formFields: [{ type: "char", name: "name", fillWith: "name", string: "Your Name" }],
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

test("'Author' field's type stays selected when you modify the option list", async () => {
    onRpc("get_authorized_fields", () => ({
        author_id: {
            name: "author_id",
            relation: "res.partner",
            string: "Author",
            type: "many2one",
        },
    }));
    await setupWebsiteBuilder(
        `<section class="s_website_form" data-snippet="s_website_form" data-name="Form">
            <div class="container-fluid">
            <form action="/website/form/" method="post" class="o_mark_required" data-model_name="mail.mail">
                <div class="s_website_form_rows">
                    <div data-name="Field" class="s_website_form_field s_website_form_required" data-type="many2one">
                        <div class="row">
                            <label class="s_website_form_label" for="oyeqnysxh10b">
                                <span class="s_website_form_label_content">Author</span>
                            </label>
                        <select class="form-select s_website_form_input" required="" id="oyeqnysxh10b" name="author_id" />
                        </div>
                    </div>
                </div>
            </form>
            </div>
        </section>`
    );

    await contains(":iframe section span:contains(Author)").click();
    await contains(".hb-row[data-label='Type'] button.o-dropdown-caret:contains('Author')").click();
    expect(".o_popover [data-action-value='author_id']").toHaveClass("active");
    await contains(".hb-row button.o-dropdown-caret:contains('Add New Option')").click();
    await contains(".o_popover .o-hb-select-dropdown-item").click();
    // check that the author is still marked as selected
    await contains(".hb-row[data-label='Type'] button.o-dropdown-caret:contains('Author')").click();
    expect(".o_popover [data-action-value='author_id']").toHaveClass("active");
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

test("Set 'Message' as form success action and show/hide the message preview", async () => {
    await setupWebsiteBuilderWithSnippet("s_website_form");
    await contains(":iframe section.s_website_form").click();
    expect(".options-container[data-container-title='Form']").toHaveCount(1);

    await contains(".options-container [data-label='On Success'] button").click();
    await contains("div[data-action-id='onSuccess'][data-action-value='message']").click();
    expect(":iframe .s_website_form_end_message.d-none").toHaveCount(1);

    await contains(".options-container [data-action-id='toggleEndMessage']").click();
    expect(":iframe .o_show_form_success_message").toHaveCount(2);
    await contains(".options-container [data-action-id='toggleEndMessage']").click();
    expect(":iframe .o_show_form_success_message").toHaveCount(0);
});

const formWithCondition = `
<section class="s_website_form"><form data-model_name="mail.mail">
     <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom" data-type="char">
         <div class="row s_col_no_resize s_col_no_bgcolor">
             <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="first">
                 <span class="s_website_form_label_content">a</span>
             </label>
             <div class="col-sm">
                 <input class="form-control s_website_form_input" type="text" name="a" id="first"/>
             </div>
         </div>
     </div>
     <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_field_hidden_if d-none" data-type="char" data-visibility-dependency="a" data-visibility-comparator="set">
         <div class="row s_col_no_resize s_col_no_bgcolor">
             <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="second">
                 <span class="s_website_form_label_content">b</span>
             </label>
             <div class="col-sm">
                 <input class="form-control s_website_form_input" type="text" name="b" id="second"/>
             </div>
         </div>
     </div>
     <div class="s_website_form_submit">
        <div class="s_website_form_label"/>
        <a>Submit</a>
    </div>
</form></section>
`;

test("Remove visibility dependency on field unavailable (change first)", async () => {
    onRpc("get_authorized_fields", () => ({}));
    const { getEditor } = await setupWebsiteBuilder(formWithCondition);
    getEditor();
    await contains(":iframe input[name=a]").click();
    await contains("[data-label=Label] input").click();
    await contains("[data-label=Label] input").edit("b");
    expect(":iframe .s_website_form_field:not([data-visibility-dependency])").toHaveCount(2);
});

test("Remove visibility dependency on field unavailable (change second)", async () => {
    onRpc("get_authorized_fields", () => ({}));
    const { getEditor } = await setupWebsiteBuilder(formWithCondition);
    getEditor();
    await contains(":iframe input[name=b]").click();
    await contains("[data-label=Label] input").click();
    await contains("[data-label=Label] input").edit("a");
    expect(":iframe .s_website_form_field:not([data-visibility-dependency])").toHaveCount(2);
});
