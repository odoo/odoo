import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    clear,
    click,
    fill,
    queryOne,
    select,
    setInputFiles,
    edit,
} from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { contains, onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList(["website.form", "website.post_link", "website.form.add_other_option"]);

describe.current.tags("interaction_dev");

function checkField(inputEl, isVisible, hasError) {
    const fieldEl = inputEl.closest(".s_website_form_field");
    isVisible ? expect(fieldEl).not.toHaveClass("d-none") : expect(fieldEl).toHaveClass("d-none");
    // Inputs required for the model are never disabled.
    if (!fieldEl.matches(".s_website_form_model_required")) {
        isVisible ? expect(inputEl).toBeEnabled() : expect(inputEl).not.toBeEnabled();
    }
    hasError
        ? expect(inputEl).toHaveClass("is-invalid")
        : expect(inputEl).not.toHaveClass("is-invalid");
    hasError
        ? expect(fieldEl).toHaveClass("o_has_error")
        : expect(fieldEl).not.toHaveClass("o_has_error");
}

const formTemplate = /* html */ `
    <div id="wrapwrap">
        <section class="s_website_form pt16 pb16" data-vcss="001" data-snippet="s_website_form" data-name="Form">
            <div class="container-fluid">
                <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you">
                    <div class="s_website_form_rows row s_col_no_bgcolor">
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required" data-type="char">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="obij2aulqyau">
                                    <span class="s_website_form_label_content">Your Name</span>
                                    <span class="s_website_form_mark"> *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input o_translatable_attribute" type="text" name="name" required="1" data-fill-with="name" id="obij2aulqyau"/>
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_model_required" data-type="email">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oub62hlfgjwf">
                                    <span class="s_website_form_label_content">Your Email</span>
                                    <span class="s_website_form_mark"> *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input o_translatable_attribute" type="email" name="email_from" required="" data-fill-with="email" id="oub62hlfgjwf"/>
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_model_required s_website_form_field_hidden_if d-none" data-type="char" data-visibility-dependency="email_from" data-visibility-comparator="set">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oqsf4m51acj">
                                    <span class="s_website_form_label_content">Subject</span>
                                    <span class="s_website_form_mark"> *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input o_translatable_attribute" type="text" name="subject" required="" id="oqsf4m51acj"/>
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required s_website_form_field_hidden_if d-none" data-type="text" data-visibility-dependency="subject" data-visibility-comparator="set">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oyeqnysxh10b">
                                    <span class="s_website_form_label_content">Your Question</span>
                                    <span class="s_website_form_mark"> *</span>
                                </label>
                                <div class="col-sm">
                                    <textarea class="form-control s_website_form_input o_translatable_text" name="description" required="1" id="oyeqnysxh10b" rows="3"></textarea>
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_dnone">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px">
                                    <span class="s_website_form_label_content"/>
                                </label>
                                <div class="col-sm">
                                    <input type="hidden" class="form-control s_website_form_input o_translatable_attribute" name="email_to" value="info@yourcompany.example.com"/>
                                </div>
                            </div>
                        </div>
                        <div class="mb-0 py-2 col-12 s_website_form_submit text-end s_website_form_no_submit_label" data-name="Submit Button">
                            <div style="width: 200px;" class="s_website_form_label"></div>
                            <span id="s_website_form_result"></span>
                            <a href="#" role="button" class="btn btn-primary s_website_form_send">Submit</a>
                        </div>
                    </div>
                </form>
            </div>
        </section>
    </div>
`;

const formWithRestrictedFieldsTemplate = /* html */ `
    <div id="wrapwrap">
        <section class="s_website_form pt16 pb16" data-vcss="001" data-snippet="s_website_form" data-name="Form">
            <div class="container-fluid">
                <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you">
                    <div class="s_website_form_rows row s_col_no_bgcolor">
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_dnone">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px">
                                    <span class="s_website_form_label_content"></span>
                                </label>
                                <div class="col-sm">
                                    <input type="hidden" class="form-control s_website_form_input" name="email_to" value="info@yourcompany.example.com">
                                    <input type="hidden" value="08db0e335821ca759f38eb45c7c30f283406f390d04dcaec27402bddf24fc29a" class="form-control s_website_form_input s_website_form_custom" name="website_form_signature">
                                </div>
                            </div>
                        </div>
                        <div data-requirement-comparator="substring" data-requirement-condition="[{&quot;requirement_text&quot;:&quot;hello&quot;,&quot;_id&quot;:&quot;0&quot;,&quot;id&quot;:&quot;hello&quot;},{&quot;requirement_text&quot;:&quot;noway&quot;,&quot;_id&quot;:&quot;1&quot;,&quot;id&quot;:&quot;noway&quot;}]" data-error-message="This field must contain one of the keyword(s): 'hello and noway'" data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required" data-type="char" data-translated-name="Your Name">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="o5vq2ntfwjaw">
                                    <span class="s_website_form_label_content">Your Name</span>
                                    <span class="s_website_form_mark">  *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input" type="text" name="name" required="" placeholder="" id="o5vq2ntfwjaw" data-fill-with="name">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom" data-type="tel" data-translated-name="Phone Number">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="omoup6x3w5bn">
                                    <span class="s_website_form_label_content">Phone Number</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input" type="tel" name="phone" placeholder="" id="omoup6x3w5bn" data-fill-with="phone">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_model_required" data-type="email" data-translated-name="Your Email">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="odfcbsocir26">
                                    <span class="s_website_form_label_content">Your Email</span>
                                    <span class="s_website_form_mark">  *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input" type="email" name="email_from" required="" placeholder="" id="odfcbsocir26" data-fill-with="email">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom" data-type="char" data-translated-name="Your Company">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="ovrzgf0mlvte">
                                    <span class="s_website_form_label_content">Your Company</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input" type="text" name="company" value="" placeholder="" id="ovrzgf0mlvte" data-fill-with="parent_name">
                                </div>
                            </div>
                        </div>
                        <div data-requirement-comparator="!substring" data-requirement-condition="[{&quot;requirement_text&quot;:&quot;football&quot;,&quot;_id&quot;:&quot;0&quot;,&quot;id&quot;:&quot;football&quot;},{&quot;requirement_text&quot;:&quot;cricket&quot;,&quot;_id&quot;:&quot;1&quot;,&quot;id&quot;:&quot;cricket&quot;}]" data-error-message="This field must not include the keyword(s): 'football and cricket'" data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_model_required" data-type="char" data-translated-name="Subject">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="ogrut2y7e6ld">
                                    <span class="s_website_form_label_content">Subject</span>
                                    <span class="s_website_form_mark">  *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input" type="text" name="subject" required="" value="" placeholder="" id="ogrut2y7e6ld" data-fill-with="undefined">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required" data-type="text" data-translated-name="Your Question">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oy6r2kn10k1">
                                    <span class="s_website_form_label_content">Your Question</span>
                                    <span class="s_website_form_mark">  *</span>
                                </label>
                                <div class="col-sm">
                                    <textarea class="form-control s_website_form_input" name="description" required="" placeholder="" id="oy6r2kn10k1" rows="3"></textarea>
                                </div>
                            </div>
                        </div>
                        <div class="mb-0 py-2 col-12 s_website_form_submit text-end s_website_form_no_submit_label" data-name="Submit Button">
                            <div style="width: 200px;" class="s_website_form_label"></div>
                            <span id="s_website_form_result"></span>
                            <a href="#" role="button" class="btn btn-primary s_website_form_send">Submit</a>
                        </div>
                    </div>
                </form>
            </div>
        </section>
    </div>
`;

function createFileUploadForm(maxFiles = 1) {
    return `
        <div id="wrapwrap">
            <section class="s_website_form" data-vcss="001" data-snippet="s_website_form" data-name="Form">
                <div class="container-fluid">
                    <form action="/website/form/" method="post" enctype="multipart/form-data"
                          class="o_mark_required" data-mark="*" data-pre-fill="true"
                          data-model_name="mail.mail" data-success-mode="redirect"
                          data-success-page="/contactus-thank-you">
                        <div class="s_website_form_rows row s_col_no_bgcolor">
                            <div data-name="Field" class="s_website_form_field mb-3 col-12
                                s_website_form_custom s_website_form_required pb0 o_colored_level"
                                data-type="binary">
                                <div class="row s_col_no_resize s_col_no_bgcolor">
                                    <label class="col-sm-auto s_website_form_label" style="width: 200px" for="o3xe8o85w0ct">
                                        <span class="s_website_form_label_content">File Upload</span>
                                        <span class="s_website_form_mark">*</span>
                                    </label>
                                    <div class="col-sm">
                                        <div class="o_files_zone row gx-1"></div>
                                        <input type="file" class="form-control s_website_form_input"
                                            name="File Upload" required id="o3xe8o85w0ct"
                                           ${
                                               maxFiles > 1 ? "multiple" : ""
                                           } data-max-files-number="${maxFiles}" data-max-file-size="64">
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="s_website_form_submit">
                            <div class="s_website_form_label"/>
                            <a>Submit</a>
                        </div>
                    </form>
                </div>
            </section>
        </div>
    `;
}

const formWithVisibilityRulesTemplate = /* html */ `
    <div id="wrapwrap">
        <section class="s_website_form pt16 pb16" data-vcss="001" data-snippet="s_website_form" data-name="Form">
            <div class="container-fluid">
                <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you">
                    <div class="s_website_form_rows row s_col_no_bgcolor">
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_dnone">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px">
                                    <span class="s_website_form_label_content"></span>
                                </label>
                                <div class="col-sm">
                                    <input type="hidden" class="form-control s_website_form_input o_translatable_attribute" name="email_to" value="info@yourcompany.example.com">
                                    <input type="hidden" value="1239f1d1c0d16680501b9974762f153fa21f4fb29aeb982c9b888f22d49cb56e" class="form-control s_website_form_input s_website_form_custom o_translatable_attribute" name="website_form_signature">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_model_required" data-type="email">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oub62hlfgjwf">
                                    <span class="s_website_form_label_content">Your Email</span>
                                    <span class="s_website_form_mark"> *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input o_translatable_attribute" type="email" name="email_from" required="" data-fill-with="email" id="oub62hlfgjwf">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_model_required" data-type="char">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oqsf4m51acj">
                                    <span class="s_website_form_label_content">Subject</span>
                                    <span class="s_website_form_mark"> *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input o_translatable_attribute" type="text" name="subject" required="" id="oqsf4m51acj">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom" data-type="char">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oea48nwznnp">
                                    <span class="s_website_form_label_content">FieldA</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input o_translatable_attribute" type="text" name="FieldA" id="oea48nwznnp">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_field_hidden_if d-none" data-type="char" data-visibility-dependency="FieldA" data-visibility-comparator="equal" data-visibility-condition="foo">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="o42sfafdr6r9">
                                    <span class="s_website_form_label_content">FieldB</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input o_translatable_attribute" type="text" name="FieldB" id="o42sfafdr6r9" disabled="disabled">
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_field_hidden_if d-none" data-type="char" data-visibility-dependency="FieldB" data-visibility-comparator="equal" data-visibility-condition="foo">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="onhykjagdxb">
                                    <span class="s_website_form_label_content">FieldC</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input o_translatable_attribute" type="text" name="FieldC" id="onhykjagdxb" disabled="disabled">
                                </div>
                            </div>
                        </div>
                        <div class="mb-0 py-2 col-12 s_website_form_submit text-end s_website_form_no_submit_label" data-name="Submit Button">
                            <div style="width: 200px;" class="s_website_form_label"></div>
                            <span id="s_website_form_result"></span>
                            <a href="#" role="button" class="btn btn-primary s_website_form_send">Submit</a>
                        </div>
                    </div>
                </form>
            </div>
        </section>
    </div>
`;

const formTemplateWithRadioAndSelect = /* html */ `
    <div id="wrapwrap">
        <section class="s_website_form">
            <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-model_name="mail.mail">
                <div data-name="Field" class="s_website_form_field">
                    <input class="form-control s_website_form_input" type="email" name="email_from" id="o15u8g10ugoy">
                </div>
                <div data-name="Field" class="s_website_form_field">
                    <input class="form-control s_website_form_input" type="text" name="subject" id="o7r4gf8heilh">
                </div>
                <div data-name="Field" class="s_website_form_field s_website_form_custom" data-type="selection" data-other-option-allowed="true" data-other-option-label="Other" data-other-option-placeholder="Other option... (radio)">
                    <div class="row s_website_form_multiple" data-name="Radio Button">
                        <div class="form-check">
                            <input type="radio" class="s_website_form_input form-check-input" id="obd2szn9ilqn0" name="Radio Button" value="Option 1" required="">
                            <label class="form-check-label s_website_form_check_label" for="obd2szn9ilqn0">Option 1</label>
                        </div>
                    </div>
                </div>
                <div data-name="Field" class="s_website_form_field s_website_form_custom" data-type="many2one" data-other-option-allowed="true" data-other-option-label="Other" data-other-option-placeholder="Other option... (select)">
                    <select class="form-select s_website_form_input" name="Select" required="" id="oo7t6wykitto">
                        <option id="oo7t6wykitto0" value="Option 1" selected>Option 1</option>
                    </select>
                </div>
                <div class="s_website_form_submit">
                    <span id="s_website_form_result"></span>
                    <a href="#" role="button" class="btn btn-primary s_website_form_send" contenteditable="true">Submit</a>
                </div>
            </form>
        </section>
    </div>
`;

// TODO Split in distinct tests.

test("form checks fields", async () => {
    const { core } = await startInteractions(formTemplate);
    expect(core.interactions).toHaveLength(1);
    expect(queryOne("form input[name=name]")).toHaveValue("Mitchell Admin");
    expect(queryOne("form input[name=email_from]")).toHaveValue("");
    expect(queryOne("form input[name=subject]")).not.toBe(undefined);
    expect(queryOne("form textarea[name=description]")).not.toBe(undefined);
    expect(queryOne("form a.s_website_form_send")).not.toBe(undefined);
});

test("(name) form checks conditions and should focus the first invalid field on submit", async () => {
    await startInteractions(formTemplate);
    const nameEl = queryOne("input[name=name]");

    checkField(nameEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(nameEl, true, false);
    // Fill mail
    expect("input[name=email_from]").toBeFocused();
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(nameEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(nameEl, true, false);
    // Fill subject
    expect("input[name=subject]").toBeFocused();
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(nameEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(nameEl, true, false);
    // Fill question
    expect("textarea[name=description]").toBeFocused();
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkField(nameEl, true, false);
    // Submit
    onRpc("/website/form/mail.mail", async () => ({}));
    await click("a.s_website_form_send");
    checkField(nameEl, true, false);
});

test("max file upload limit = 1", async () => {
    const fileUploadForm = createFileUploadForm();
    await startInteractions(fileUploadForm);
    const file = new File(["fake_file"], "fake_file.pdf", { type: "application/pdf" });
    await contains(".s_website_form input[type='file']").click();
    await setInputFiles([file]);
    await animationFrame();
    expect(".o_add_files_button").toHaveValue("Replace File");
});

test("max file upload limit > 1", async () => {
    const fileUploadFormMultiple = createFileUploadForm(10);
    await startInteractions(fileUploadFormMultiple);
    const file = new File(["fake_file"], "fake_file.pdf", { type: "application/pdf" });
    await contains(".s_website_form input[type='file']").click();
    await setInputFiles([file]);
    await animationFrame();
    expect(".o_add_files_button").toHaveValue("Add Files");
});

test("(mail) form checks conditions", async () => {
    await startInteractions(formTemplate);
    const mailEl = queryOne("input[name=email_from]");

    checkField(mailEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(mailEl, true, true);
    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(mailEl, true, true);
    // Submit
    await click("a.s_website_form_send");
    checkField(mailEl, true, false);
    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(mailEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(mailEl, true, false);
    // Fill question
    await click("textarea[name=description]");
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkField(mailEl, true, false);
    // Submit
    onRpc("/website/form/mail.mail", async () => ({}));
    await click("a.s_website_form_send");
    checkField(mailEl, true, false);
});

test("(subject) form checks conditions", async () => {
    await startInteractions(formTemplate);
    const subjectEl = queryOne("input[name=subject]");

    checkField(subjectEl, false, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(subjectEl, false, true);
    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(subjectEl, true, true);
    // Submit
    await click("a.s_website_form_send");
    checkField(subjectEl, true, true);
    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(subjectEl, true, true);
    // Submit
    await click("a.s_website_form_send");
    checkField(subjectEl, true, false);
    // Fill question
    await click("textarea[name=description]");
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkField(subjectEl, true, false);
    // Submit
    onRpc("/website/form/mail.mail", async () => ({}));
    await click("a.s_website_form_send");
    checkField(subjectEl, true, false);
});

test("(question) form checks conditions", async () => {
    await startInteractions(formTemplate);
    const questionEl = queryOne("textarea[name=description]");

    checkField(questionEl, false, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(questionEl, false, false);
    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(questionEl, false, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(questionEl, false, false);
    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(questionEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(questionEl, true, true);
    // Fill question
    await click("textarea[name=description]");
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkField(questionEl, true, true);
    // Submit
    onRpc("/website/form/mail.mail", async () => ({}));
    await click("a.s_website_form_send");
    checkField(questionEl, true, false);
});

test("(rpc) form checks conditions", async () => {
    await startInteractions(formTemplate);

    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.

    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.

    // Fill question
    await click("textarea[name=description]");
    await fill("Question");
    await advanceTime(400); // Debounce delay.

    let rpcCheck = false;
    const rpcDone = Promise.withResolvers();
    onRpc("/website/form/mail.mail", async (args) => {
        rpcCheck = true;
        rpcDone.resolve();
        return {};
    });
    await click("a.s_website_form_send");
    await rpcDone.promise;
    expect(rpcCheck).toBe(true);
});

test("form submit result cleaned but not removed on stop", async () => {
    const { core } = await startInteractions(formTemplate);
    expect(core.interactions).toHaveLength(1);
    expect(queryOne("#s_website_form_result").children.length).toEqual(0);
    await click("a.s_website_form_send");
    expect(queryOne("#s_website_form_result").children.length).toEqual(1);
    core.stopInteractions();
    expect(queryOne("#s_website_form_result").children.length).toEqual(0);
});

function formWithVisibilityRulesOnCheckbox(condition) {
    return `
        <section class="s_website_form">
            <form data-model_name="mail.mail">
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
                <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_field_hidden_if d-none" data-type="char" data-visibility-dependency="Custom Text" data-visibility-condition='["Option 1","Option 2"]' data-visibility-comparator="${condition}">
                    <div class="row s_col_no_resize s_col_no_bgcolor">
                        <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="second">
                            <span class="s_website_form_label_content">b</span>
                        </label>
                        <div class="col-sm">
                            <input class="form-control s_website_form_input" type="text" name="b" id="second"/>
                        </div>
                    </div>
                </div>
            </form>
        </section>
    `;
}

test("contains conditional visibility(multiple checkbox)", async () => {
    const { core } = await startInteractions(formWithVisibilityRulesOnCheckbox("contains"));
    const fieldB = ".s_website_form_field:has(input[name=b])";
    expect(core.interactions).toHaveLength(1);
    expect(fieldB).not.toBeVisible();

    await contains("input[value='Option 3']").click();
    await advanceTime(400); // Debounce delay.
    expect(fieldB).not.toBeVisible();

    await contains("input[value='Option 2']").click();
    await advanceTime(400); // Debounce delay.
    expect(fieldB).toBeVisible();

    await contains("input[value='Option 1']").click();
    await advanceTime(400); // Debounce delay.
    expect(fieldB).toBeVisible();
});

test("does't contains conditional visibility(multiple checkbox)", async () => {
    const { core } = await startInteractions(formWithVisibilityRulesOnCheckbox("!contains"));
    const fieldB = ".s_website_form_field:has(input[name=b])";
    expect(core.interactions).toHaveLength(1);
    expect(fieldB).toBeVisible();

    await contains("input[value='Option 3']").click();
    await advanceTime(400); // Debounce delay.
    expect(fieldB).toBeVisible();

    await contains("input[value='Option 2']").click();
    await advanceTime(400); // Debounce delay.
    expect(fieldB).not.toBeVisible();

    await contains("input[value='Option 1']").click();
    await advanceTime(400); // Debounce delay.
    expect(fieldB).not.toBeVisible();
});

function formWithVisibilityRulesOnText(condition) {
    return `
        <section class="s_website_form">
            <form data-model_name="mail.mail">
                <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom" data-type="char">
                    <div class="row s_col_no_resize s_col_no_bgcolor">
                        <label class="col-sm-auto s_website_form_label" style="width: 200px" for="ofwe8fyqws37">
                            <span class="s_website_form_label_content">a</span>
                        </label>
                        <div class="col-sm">
                            <input class="form-control s_website_form_input" type="text" name="a" required="1" id="obij2aulqyau"/>
                        </div>
                    </div>
                </div>
                <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_field_hidden_if d-none" data-type="char" data-visibility-dependency="a" data-visibility-condition='test' data-visibility-comparator="${condition}">
                    <div class="row s_col_no_resize s_col_no_bgcolor">
                        <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="second">
                            <span class="s_website_form_label_content">b</span>
                        </label>
                        <div class="col-sm">
                            <input class="form-control s_website_form_input" type="text" name="b" id="second"/>
                        </div>
                    </div>
                </div>
            </form>
        </section>
    `;
}

test("contains conditional visibility(text input)", async () => {
    const { core } = await startInteractions(formWithVisibilityRulesOnText("contains"));
    const fieldB = ".s_website_form_field:has(input[name=b])";
    expect(core.interactions).toHaveLength(1);
    expect(fieldB).not.toBeVisible();

    await contains("input[name=a]").click();
    await fill("something");
    await advanceTime(400); // Debounce delay.
    expect(fieldB).not.toBeVisible();

    await contains("input[name=a]").click();
    await fill("test string");
    await advanceTime(400); // Debounce delay.
    expect(fieldB).toBeVisible();
});

test("doesn't contains conditional visibility(text input)", async () => {
    const { core } = await startInteractions(formWithVisibilityRulesOnText("!contains"));
    const fieldB = ".s_website_form_field:has(input[name=b])";
    expect(core.interactions).toHaveLength(1);
    expect(fieldB).toBeVisible();

    await contains("input[name=a]").click();
    await fill("something");
    await advanceTime(400); // Debounce delay.
    expect(fieldB).toBeVisible();

    await contains("input[name=a]").click();
    await fill("test string");
    await advanceTime(400); // Debounce delay.
    expect(fieldB).not.toBeVisible();
});

test("form prefilled conditional", async () => {
    onRpc("res.users", "read", ({ parent }) => {
        const result = parent();
        result[0].phone = "+1-555-5555";
        return result;
    });

    // Phone number is only visible if name is filled.
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <section class="s_website_form pt16 pb16" data-vcss="001" data-snippet="s_website_form" data-name="Form">
                <div class="container-fluid">
                    <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you">
                        <div class="s_website_form_rows row s_col_no_bgcolor">
                            <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_required" data-type="char">
                                <div class="row s_col_no_resize s_col_no_bgcolor">
                                    <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="obij2aulqyau">
                                        <span class="s_website_form_label_content">Your Name</span>
                                        <span class="s_website_form_mark"> *</span>
                                    </label>
                                    <div class="col-sm">
                                        <input class="form-control s_website_form_input" type="text" name="name" required="1" data-fill-with="name" id="obij2aulqyau"/>
                                    </div>
                                </div>
                            </div>
                            <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom s_website_form_field_hidden_if d-none" data-type="tel"
                                    data-visibility-dependency="name"
                                    data-visibility-comparator="set"
                            >
                                <div class="row s_col_no_resize s_col_no_bgcolor">
                                    <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="ozp7022vqhe">
                                        <span class="s_website_form_label_content">Phone Number</span>
                                    </label>
                                    <div class="col-sm">
                                        <input class="form-control s_website_form_input" type="tel" name="phone" data-fill-with="phone" id="ozp7022vqhe"/>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </section>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    expect(queryOne("form input[name=name]")).toHaveValue("Mitchell Admin");
    expect(queryOne("form input[name=phone]")).toHaveValue("+1-555-5555");
});

test("form elements chained conditional visibility", async () => {
    await startInteractions(formWithVisibilityRulesTemplate);
    const fieldA = queryOne("input[name=FieldA]");
    const fieldB = queryOne("input[name=FieldB]");
    const fieldC = queryOne("input[name=FieldC]");
    checkField(fieldB, false, false);
    checkField(fieldC, false, false);
    await click(fieldA);
    await fill("foo");
    await advanceTime(400); // Debounce delay.
    checkField(fieldB, true, false);
    checkField(fieldC, false, false);
    await click(fieldB);
    await fill("foo");
    await advanceTime(400); // Debounce delay.
    checkField(fieldB, true, false);
    checkField(fieldC, true, false);
    await click(fieldA);
    await clear();
    await advanceTime(400); // Debounce delay.
    checkField(fieldB, false, false);
    checkField(fieldC, false, false);
    await click(fieldA);
    await fill("foo");
    await advanceTime(400); // Debounce delay.
    checkField(fieldB, true, false);
    checkField(fieldC, true, false);
});

test("should make 'Other' input fields required when 'Other' option is selected", async () => {
    await startInteractions(formTemplateWithRadioAndSelect);
    const selectOtherInputEl = queryOne(".o_other_input[placeholder='Other option... (select)']");
    const radioOtherInputEl = queryOne(".o_other_input[placeholder='Other option... (radio)']");

    await contains("input[name=email_from]").fill("a@b.com");
    await contains("input[name=subject]").fill("Subject");
    await click(".form-select");
    await select("_other");
    await click("a.s_website_form_send");
    checkField(selectOtherInputEl, true, true);

    await contains(selectOtherInputEl).fill("Other option input for select");
    await click(".s_website_form_input[value='_other']");
    await click("a.s_website_form_send");
    checkField(radioOtherInputEl, true, true);

    await contains(radioOtherInputEl).fill("Other option input for radio");
    // Wait for the debounced input event to update the form state.
    await advanceTime(400);
    onRpc("/website/form/mail.mail", async (request) => {
        const formData = await request.formData();
        expect(formData.get("Radio Button")).toBe("Other option input for radio");
        expect.step("Valid Radio Value");
        expect(formData.get("Select")).toBe("Other option input for select");
        expect.step("Valid Select Value");
    });
    await click("a.s_website_form_send");
    expect.verifySteps(["Valid Radio Value", "Valid Select Value"]);
});

test("check multi-input field restrictions on email and text fields.", async () => {
    const { core } = await startInteractions(formWithRestrictedFieldsTemplate);
    expect(core.interactions).toHaveLength(1);
    const nameEl = queryOne("input[name=name]");
    const subjectEl = queryOne("input[name=subject]");
    const emailEl = queryOne("input[name=email_from]");
    // Fill name with a value that doesn't meet the requirement.
    await click(nameEl);
    await edit("John Doe");
    await advanceTime(400);
    await click("a.s_website_form_send");
    checkField(nameEl, true, true);
    // Fill name with a value that meets the requirement.
    await click(nameEl);
    await edit("hello world");
    await advanceTime(400);
    await click("a.s_website_form_send");
    checkField(nameEl, true, false);
    // Fill subject with a value that doesn't meet the requirement.
    await click(subjectEl);
    await edit("Good game of football");
    await advanceTime(400);
    await click("a.s_website_form_send");
    checkField(subjectEl, true, true);
    // Fill subject with a value that meets the requirement.
    await click(subjectEl);
    await edit("This is a long enough subject");
    await advanceTime(400);
    await click("a.s_website_form_send");
    checkField(subjectEl, true, false);
});
