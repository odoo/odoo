import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { expectElementCount } from "@html_editor/../tests/_helpers/ui_expectations";
import { beforeEach, describe, expect, press, queryOne, test, waitFor } from "@odoo/hoot";
import { animationFrame, edit } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    MockServer,
    models,
    onRpc,
    webModels,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

class HrJob extends models.Model {
    _name = "hr.job";
}
defineModels([HrJob]);

patch(webModels.IrModel.prototype, {
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

    await setupWebsiteBuilderWithSnippet("s_website_form");

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
    await contains(".o_select_menu button.o-hb-selectMany2X-toggle:contains('Add')").click();
    await contains(".o_select_menu_menu .o-dropdown-item").click();
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

const formWithConditionOnChexbox = `
<section class="s_website_form"><form data-model_name="mail.mail">
    <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom" data-type="one2many">
        <div class="row s_col_no_resize s_col_no_bgcolor">
            <label class="col-sm-auto s_website_form_label" style="width: 200px" for="ofwe8fyqws37">
                <span class="s_website_form_label_content">Custom Text</span>
            </label>
            <div class="col-sm">
                <div class="row s_col_no_resize s_col_no_bgcolor s_website_form_multiple" data-name="Custom Text" data-display="horizontal">
                    <div class="checkbox col-12 col-lg-4 col-md-6">
                        <div class="form-check">
                            <input type="checkbox" class="s_website_form_input form-check-input" id="ofwe8fyqws370" name="Custom Text" value="Option 1" data-fill-with="undefined">
                            <label class="form-check-label s_website_form_check_label" for="ofwe8fyqws370">Option 1</label>
                        </div>
                    </div>
                    <div class="checkbox col-12 col-lg-4 col-md-6">
                        <div class="form-check">
                            <input type="checkbox" class="s_website_form_input form-check-input" id="ofwe8fyqws371" name="Custom Text" value="Option 2">
                            <label class="form-check-label s_website_form_check_label" for="ofwe8fyqws371">Option 2</label>
                        </div>
                    </div>
                    <div class="checkbox col-12 col-lg-4 col-md-6">
                        <div class="form-check">
                            <input type="checkbox" class="s_website_form_input form-check-input" id="ofwe8fyqws372" name="Custom Text" value="Option 3">
                            <label class="form-check-label s_website_form_check_label" for="ofwe8fyqws372">Option 3</label>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
     <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_field_hidden_if d-none" data-type="char" data-visibility-dependency="Custom Text" data-visibility-condition="Option 1" data-visibility-comparator="selected">
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

const changeFieldAndCheckDependency = async (
    changeFieldAction,
    fieldDependencyName = "Option 1"
) => {
    onRpc("get_authorized_fields", () => ({}));
    await setupWebsiteBuilder(formWithConditionOnChexbox);
    await contains(":iframe input[value='Option 2']").click();
    await changeFieldAction();
    await contains(":iframe input[name='b']").click();
    await contains(`#hidden_condition_no_text_opt:contains(${fieldDependencyName})`).click();
};

test("Correctly set field dependency name at field rename", async () => {
    await changeFieldAndCheckDependency(
        async () => await contains("input[data-id='1']").edit("newName")
    );
    expect(".o-main-components-container  .o-dropdown-item:contains('Option 3')").toHaveCount(1);
    expect(".o-main-components-container  .o-dropdown-item:contains('newName')").toHaveCount(1);
});

test("Correctly set field dependency name at field addition", async () => {
    await changeFieldAndCheckDependency(
        async () => await contains("button.builder_list_add_item").click()
    );
    expect(".o-main-components-container  .o-dropdown-item:contains('Option 2')").toHaveCount(1);
    expect(".o-main-components-container  .o-dropdown-item:contains('Option 3')").toHaveCount(1);
    expect(".o-main-components-container  .o-dropdown-item:contains('Item')").toHaveCount(1);
});

test("Correctly set field dependency name at selected field rename", async () => {
    const newName = "newName";
    await changeFieldAndCheckDependency(
        async () => await contains("input[data-id='0']").edit(newName),
        newName
    );
    expect(".o-main-components-container  .o-dropdown-item:contains('Option 3')").toHaveCount(1);
    expect(".o-main-components-container  .o-dropdown-item:contains('Option 2')").toHaveCount(1);
    expect(`.o-main-components-container  .o-dropdown-item:contains('${newName}')`).toHaveCount(1);
});

test("Changing max files number option updates file input 'multiple' attribute", async () => {
    onRpc("get_authorized_fields", () => ({}));
    await setupWebsiteBuilder(`
    <section class="s_website_form" data-vcss="001" data-snippet="s_website_form" data-name="Form">
        <form data-model_name="mail.mail">
            <div class="s_website_form_rows">
                <div data-name="Field" class="s_website_form_field s_website_form_custom" data-type="binary">
                    <label class="s_website_form_label" for="o3xe8o85w0ct">
                        <span class="s_website_form_label_content">File Upload</span>
                    </label>
                    <input type="file" class="form-control s_website_form_input"
                        name="File Upload" required id="o3xe8o85w0ct"
                        data-max-files-number="1" data-max-file-size="64">
                </div>
            </div>
        </form>
    </section>
        `);
    expect(":iframe input[type=file]").toHaveAttribute("data-max-files-number", "1");
    expect(":iframe input[type=file]").not.toHaveAttribute("multiple");
    await contains(":iframe .s_website_form_input").click();
    await contains(".options-container div[data-action-id='setMultipleFiles'] input").edit("2");
    expect(":iframe input[type=file]").toHaveAttribute("data-max-files-number", "2");
    expect(":iframe input[type=file]").toHaveAttribute("multiple");
    await contains(":iframe .s_website_form_input").click();
    await contains(".options-container div[data-action-id='setMultipleFiles'] input").edit("1");
    expect(":iframe input[type=file]").toHaveAttribute("data-max-files-number", "1");
    expect(":iframe input[type=file]").not.toHaveAttribute("multiple");
});

test("Form using the Outgoing Mails model includes hidden email_to field", async () => {
    await setupWebsiteBuilder(
        `<section class="s_website_form">
            <form data-model_name="mail.mail">
                <div class="s_website_form_submit">
                    <div class="s_website_form_label"/>
                    <a>Submit</a>
                </div>
            </form>
        </section>`
    );

    await contains(":iframe section").click();
    await contains("div:has(>span:contains('Action')) + div button").click();
    await contains("div.o-dropdown-item:contains('Send an E-mail')").click();

    expect(":iframe input[type='hidden'][name='email_to']").toHaveCount(1);
    expect(":iframe input[type='hidden'][name='email_to']").toHaveValue(
        "info@yourcompany.example.com"
    );
});

test("Last list entry cannot be removed", async () => {
    onRpc("get_authorized_fields", () => ({}));
    await setupWebsiteBuilder(`
<section class="s_website_form" data-vcss="001" data-snippet="s_website_form" data-name="Form">
    <form data-model_name="mail.mail">
        <div class="s_website_form_rows">
			<div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom" data-type="one2many">
			    <div class="row s_col_no_resize s_col_no_bgcolor">
			        <label class="col-sm-auto s_website_form_label" style="width: 200px" for="ofwe8fyqws37">
			            <span class="s_website_form_label_content">Custom Text</span>
			        </label>
			        <div class="col-sm">
			            <div class="row s_col_no_resize s_col_no_bgcolor s_website_form_multiple" data-name="Custom Text" data-display="horizontal">
			                <div class="checkbox col-12 col-lg-4 col-md-6">
			                    <div class="form-check">
			                        <input type="checkbox" class="s_website_form_input form-check-input" id="ofwe8fyqws370" name="Custom Text" value="Option 1" data-fill-with="undefined">
			                        <label class="form-check-label s_website_form_check_label" for="ofwe8fyqws370">Option 1</label>
			                    </div>
			                </div>
			                <div class="checkbox col-12 col-lg-4 col-md-6">
			                    <div class="form-check">
			                        <input type="checkbox" class="s_website_form_input form-check-input" id="ofwe8fyqws371" name="Custom Text" value="Option 2">
			                        <label class="form-check-label s_website_form_check_label" for="ofwe8fyqws371">Option 2</label>
			                    </div>
			                </div>
			                <div class="checkbox col-12 col-lg-4 col-md-6">
			                    <div class="form-check">
			                        <input type="checkbox" class="s_website_form_input form-check-input" id="ofwe8fyqws372" name="Custom Text" value="Option 3">
			                        <label class="form-check-label s_website_form_check_label" for="ofwe8fyqws372">Option 3</label>
			                    </div>
			                </div>
			            </div>
			        </div>
			    </div>
            </div>
	    </div>
    </form>
</section>
        `);
    await contains(":iframe .s_website_form_field").click();
    expect(".options-container .builder_list_remove_item").toHaveCount(3);
    await contains(
        ".options-container .o_row_draggable:has(input[data-id='0']) .builder_list_remove_item"
    ).click();
    expect(".options-container .builder_list_remove_item").toHaveCount(2);
    await contains(
        ".options-container .o_row_draggable:has(input[data-id='1']) .builder_list_remove_item"
    ).click();
    expect(".options-container .builder_list_remove_item").toHaveCount(0);
    await contains(".options-container .builder_list_add_item").click();
    expect(".options-container .builder_list_remove_item").toHaveCount(2);
});

test("Can link states to a country", async () => {
    onRpc("get_authorized_fields", () => ({}));
    await setupWebsiteBuilder(
        `<section class="s_website_form"><form data-model_name="mail.mail">
            <div data-name="Country" class="s_website_form_field s_website_form_custom" data-type="many2one">
                <div>
                    <label class="s_website_form_label" for="country">
                        <span class="s_website_form_label_content">Country</span>
                    </label>
                    <div>
                        <select class="form-select s_website_form_input" name="country_id" id="country">
                            <option value=""></option>
                            <option value="1" selected="selected">Country 1 (A)</option>
                            <option value="2">Country 2 (B)</option>
                        </select>
                    </div>
                </div>
            </div>
            <div data-name="State" class="s_website_form_field s_website_form_custom" data-type="many2one">
                <div>
                    <label class="s_website_form_label" for="state">
                        <span class="s_website_form_label_content">State</span>
                    </label>
                    <div>
                        <select class="form-select s_website_form_input" name="state_id" id="state">
                            <option value=""></option>
                            <option data-country-id="1" value="s1">State 1 (A)</option>
                            <option data-country-id="2" value="s2">State 2 (B)</option>
                        </select>
                    </div>
                </div>
            </div>
        </form></section>`
    );
    await contains(":iframe select[name='state_id']").click();
    expect(".options-container .hb-row [data-action-id='linkStateToCountry']").toHaveCount(1);
    expect(
        ".options-container .hb-row [data-action-id='linkStateToCountry'] input"
    ).not.toBeChecked();
    expect(".options-container .hb-row p:contains('Option List')").toHaveCount(1);

    await contains(
        ".options-container .hb-row [data-action-id='linkStateToCountry'] input"
    ).click();

    expect(".options-container .hb-row [data-action-id='linkStateToCountry'] input").toBeChecked();
    expect(".options-container .hb-row :contains('Option List')").toHaveCount(0);
    expect(":iframe select[name='state_id']").toHaveAttribute("data-link-state-to-country", "true");
});

test("Shouldn't have the 'Link to country' option if there's no country field", async () => {
    onRpc("get_authorized_fields", () => ({}));
    await setupWebsiteBuilder(
        `<section class="s_website_form"><form data-model_name="mail.mail">
            <div data-name="State" class="s_website_form_field s_website_form_custom" data-type="many2one">
                <div>
                    <label class="s_website_form_label" for="state">
                        <span class="s_website_form_label_content">State</span>
                    </label>
                    <div>
                        <select class="form-select s_website_form_input" name="state_id" id="state">
                            <option value=""></option>
                            <option data-country-id="1" value="s1">State 1 (A)</option>
                            <option data-country-id="2" value="s2">State 2 (B)</option>
                        </select>
                    </div>
                </div>
            </div>
        </form></section>`
    );
    await contains(":iframe select[name='state_id']").click();
    expect(".options-container .hb-row[data-action-id='linkStateToCountry']").toHaveCount(0);
});

test("Label falls back to default value (data-translated-name) when removed", async () => {
    onRpc("get_authorized_fields", () => ({}));
    await setupWebsiteBuilder(
        `<section class="s_website_form" data-snippet="s_website_form" data-name="Form">
            <div class="container-fluid">
            <form action="/website/form/" method="post" class="o_mark_required" data-model_name="mail.mail">
                <div class="s_website_form_rows">
                    <div data-name="Field" data-translated-name="Default value" class="s_website_form_field s_website_form_required" data-type="text">
                        <div class="row">
                            <label class="s_website_form_label" for="oyeqnysxh10b">
                                <span class="s_website_form_label_content">My Field</span>
                            </label>
                        <select class="form-select s_website_form_input" required="" id="oyeqnysxh10b" name="field" />
                        </div>
                    </div>
                </div>
            </form>
            </div>
        </section>`
    );

    await contains(":iframe section span:contains('My Field')").click();
    await contains("[data-action-id='setLabelText'] input").click();
    expect("[data-action-id='setLabelText'] input").toHaveValue("My Field");
    await edit("");
    await press("Tab");
    expect("[data-action-id='setLabelText'] input").toHaveValue("Default value");
    expect(":iframe section [data-translated-name='Default value'] label").toHaveText(
        "Default value"
    );
});

describe("Many2one Field", () => {
    const addRecordButtonSelector =
        ".we-bg-options-container .o_select_menu button.o-hb-selectMany2X-toggle";
    let records;

    beforeEach(async () => {
        onRpc("get_authorized_fields", () => ({
            country_id: {
                name: "country_id",
                relation: "res.country",
                string: "Country",
                type: "many2one",
            },
        }));
        await setupWebsiteBuilder(`
            <section class="s_website_form" data-snippet="s_website_form" data-name="Form">
                <div class="container-fluid">
                    <form action="/website/form/" method="post" class="o_mark_required" data-model_name="res.partner">
                        <div class="s_website_form_rows">
                            <div data-name="Field" class="s_website_form_field s_website_form_required" data-type="many2one">
                                <div class="row">
                                    <label class="s_website_form_label" for="oyeqnysxh10b">
                                        <span class="s_website_form_label_content">Country</span>
                                    </label>
                                    <select class="form-select s_website_form_input" required="" id="oyeqnysxh10b" name="country_id" >
                                        <option selected="selected" id="oyeqnysxh10b0" value="1">Belgium</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </section>
        `);
        const env = MockServer.env;
        records = [
            env["res.country"].create({ name: "Belgium" }),
            env["res.country"].create({ name: "Spain" }),
            env["res.country"].create({ name: "India" }),
            env["res.country"].create({ name: "Mexico" }),
            env["res.country"].create({ name: "Kenya" }),
            env["res.country"].create({ name: "US" }),
            env["res.country"].create({ name: "UAE" }),
            env["res.country"].create({ name: "Brazil" }),
        ];

        await contains(":iframe section span:contains(Country)").click();
    });

    test("At beginning", () => {
        // There should be only one option, and it should be selected
        expect(".o_we_table_wrapper table tr").toHaveCount(1);
        expect(".o_we_table_wrapper table tr input[type=checkbox]").toHaveProperty("checked");
        expect(":iframe select option").toHaveCount(1);
        expect(":iframe select option[selected]").toHaveText("Belgium");
    });

    test("No record record selected by default", async () => {
        // Disable selected
        await contains(".o_we_table_wrapper table tr input[type=checkbox]").click();
        expect(":iframe select option").toHaveCount(2, {
            message: "Disabling Belgium as selected item should add an empty item selected",
        });
        expect(":iframe select option[selected]").toHaveText("");

        // Select it back
        await contains(".o_we_table_wrapper table tr input[type=checkbox]").click();
        expect(":iframe select option[selected]").toHaveText("Belgium");
        expect(":iframe select option").toHaveCount(1, {
            message: "Select Belgium back should remove the empty item",
        });
    });

    test("SelectMenu to add records", async () => {
        await contains(addRecordButtonSelector).click();
        await expectElementCount(".o_select_menu_menu .o_select_menu_item", records.length - 1);
        expect(queryOne(".o_select_menu_menu").getBoundingClientRect().top).toBeLessThan(
            queryOne(addRecordButtonSelector).getBoundingClientRect().top,
            {
                message:
                    "The menu should be rendered above the Add button because it's too tall to be below.",
            }
        );
        expect(".o_select_menu_menu .o-dropdown-item:first").toHaveText("Brazil", {
            message:
                "Since we already added 'Belgium' the first alphabetical suggestion should be 'Brazil'",
        });
        expect(".o_select_menu_menu .o-dropdown-item:nth-of-type(2)").toHaveText("India");
        await contains(".o_select_menu_menu .o-dropdown-item:nth-of-type(2)").click();
        await contains(addRecordButtonSelector).click();
        await contains(".o_select_menu_menu .o-dropdown-item:first").click();

        expect(".o_we_table_wrapper table tr:first input[name=display_name]").toHaveValue(
            "Belgium"
        );
        expect(".o_we_table_wrapper table tr:first input[type=checkbox]").toBeChecked();
        expect(".o_we_table_wrapper table tr:nth-of-type(2) input[name=display_name]").toHaveValue(
            "India"
        );
        expect(".o_we_table_wrapper table tr:nth-of-type(3) input[name=display_name]").toHaveValue(
            "Brazil"
        );

        expect(":iframe select option").toHaveCount(3);
        expect(":iframe select option:first[selected]").toHaveText("Belgium");
        expect(":iframe select option:nth-of-type(2)").toHaveText("India");
        expect(":iframe select option:nth-of-type(3)").toHaveText("Brazil");
    });

    test("Update button", async () => {
        await contains(".we-bg-options-container .fa-refresh").click();
        expect(addRecordButtonSelector).toHaveProperty("disabled", true, {
            message: "Add button should be disabled when all records are included",
        });
        expect(".o_we_table_wrapper table tr").toHaveCount(records.length);
        expect(".o_we_table_wrapper table tr:first input[type=checkbox]").toBeChecked();
        expect(".o_we_table_wrapper table tr:nth-of-type(2) input[name=display_name]").toHaveValue(
            "Brazil",
            {
                message:
                    "Brazil should be the second element as the list should be ordered alphabetically after update",
            }
        );

        expect(":iframe select option").toHaveCount(records.length);
        expect(":iframe select option[selected]").toHaveText("Belgium");
    });

    describe("Dialog", () => {
        const dialogButtonSelector = ".we-bg-options-container .fa-gear";

        test("Add all and remove all", async () => {
            await contains(dialogButtonSelector).click();
            // Add all
            await contains(".modal-dialog .o_left_panel .fa-plus").click();
            await expectElementCount(".modal-dialog .o_left_panel .o_list_item", 0);
            await expectElementCount(".modal-dialog .o_right_panel .o_list_item", records.length);
            // Remove all
            await contains(".modal-dialog .o_right_panel .fa-minus").click();
            await expectElementCount(".modal-dialog .o_right_panel .o_list_item", 0);
            await expectElementCount(".modal-dialog .o_left_panel .o_list_item", records.length);

            expect(".modal-dialog .btn-primary").toHaveProperty("disabled");

            // Add Belgium back
            await contains(".modal-dialog .o_left_panel .o_list_item").click();
            await contains(".modal-dialog .btn-primary").click();
            expect(".o_we_table_wrapper table tr").toHaveCount(1);
            expect(".o_we_table_wrapper table tr input[name=display_name]").toHaveValue("Belgium", {
                message: "Belgium should be the first record of the dialog and the only one added",
            });

            // Belgium should still be selected
            expect(":iframe select option").toHaveCount(1);
            expect(":iframe select option[selected]").toHaveText("Belgium");
        });

        test("List order", async () => {
            await contains(addRecordButtonSelector).click();
            await contains(".o_select_menu_menu .o-dropdown-item:contains(India)").click();
            await contains(addRecordButtonSelector).click();
            await contains(".o_select_menu_menu .o-dropdown-item:contains(Brazil)").click();
            await contains(dialogButtonSelector).click();

            expect(".modal-dialog .o_left_panel .o_list_item").toHaveCount(records.length - 3);
            expect(".modal-dialog .o_right_panel .o_list_item").toHaveCount(3);

            expect(".modal-dialog .o_right_panel .o_list_item:last-child").toHaveText("Brazil", {
                message: "The right list should be ordered like it is in the sidebar",
            });
            await contains(".modal-dialog .o_left_panel .o_list_item").click();
            expect(".modal-dialog .o_right_panel .o_list_item:last-child").toHaveText("Kenya", {
                message:
                    "Kenya should have been the first of the left list and the last of the right list after being added",
            });
            await contains(".modal-dialog .btn-primary").click();
            expect(".o_we_table_wrapper table tr").toHaveCount(4);
            expect(".o_we_table_wrapper table tr:last-child input[name=display_name]").toHaveValue(
                "Kenya"
            );

            expect(":iframe select option").toHaveCount(4);
        });

        test("Search", async () => {
            await contains(dialogButtonSelector).click();

            // The search bar should focus automatically
            await waitFor("input[type=search]:focus");
            await press("m");
            await press("e");
            await animationFrame();

            expect(".modal-dialog .o_left_panel .o_list_item").toHaveText("Mexico");
            expect(".modal-dialog .o_right_panel .o_list_item").toHaveCount(0);

            await contains(".modal-dialog .o_left_panel .o_list_item").click();
            expect(".modal-dialog .o_left_panel .o_list_item").toHaveCount(0);
            expect(".modal-dialog .o_right_panel .o_list_item").toHaveText("Mexico");

            await contains("input[type=search]").click();
            await press("Backspace");
            await press("Backspace");
            await animationFrame();

            expect(".modal-dialog .o_left_panel .o_list_item").toHaveCount(records.length - 2);
            expect(".modal-dialog .o_right_panel .o_list_item").toHaveCount(2);
        });
    });
});
