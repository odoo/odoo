import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, clear, click, fill, queryOne, setInputFiles } from "@odoo/hoot-dom";
import { advanceTime, Deferred } from "@odoo/hoot-mock";

import { contains, onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList(["website.form", "website.post_link"]);

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

test("(name) form checks conditions", async () => {
    await startInteractions(formTemplate);
    const nameEl = queryOne("input[name=name]");

    checkField(nameEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(nameEl, true, false);
    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(nameEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(nameEl, true, false);
    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(nameEl, true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(nameEl, true, false);
    // Fill question
    await click("textarea[name=description]");
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
    const rpcDone = new Deferred();
    onRpc("/website/form/mail.mail", async (args) => {
        rpcCheck = true;
        rpcDone.resolve();
        return {};
    });
    await click("a.s_website_form_send");
    await rpcDone;
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
