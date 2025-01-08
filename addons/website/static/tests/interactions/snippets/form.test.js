import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { click, fill } from "@odoo/hoot-dom";
import { advanceTime, Deferred } from "@odoo/hoot-mock";

import { MockServer, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList(["website.form", "website.post_link"]);

describe.current.tags("interaction_dev");

function field(inputEl) {
    return inputEl.closest(".s_website_form_field");
}

const formTemplate = `
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
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_model_required" data-type="email">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="oub62hlfgjwf">
                                    <span class="s_website_form_label_content">Your Email</span>
                                    <span class="s_website_form_mark"> *</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input" type="email" name="email_from" required="" data-fill-with="email" id="oub62hlfgjwf"/>
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
                                    <input class="form-control s_website_form_input" type="text" name="subject" required="" id="oqsf4m51acj"/>
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
                                    <textarea class="form-control s_website_form_input" name="description" required="1" id="oyeqnysxh10b" rows="3"></textarea>
                                </div>
                            </div>
                        </div>
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_dnone">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px">
                                    <span class="s_website_form_label_content"/>
                                </label>
                                <div class="col-sm">
                                    <input type="hidden" class="form-control s_website_form_input" name="email_to" value="info@yourcompany.example.com"/>
                                </div>
                            </div>
                        </div>
                        <div class="mb-0 py-2 col-12 s_website_form_submit text-end s_website_form_no_submit_label" data-name="Submit Button">
                            <div style="width: 200px;" class="s_website_form_label"/>
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
    const { core, el } = await startInteractions(formTemplate);
    expect(core.interactions).toHaveLength(1);
    const formEl = el.querySelector("form");
    const nameEl = formEl.querySelector("input[name=name]");
    const mailEl = formEl.querySelector("input[name=email_from]");
    const subjectEl = formEl.querySelector("input[name=subject]");
    const questionEl = formEl.querySelector("textarea[name=description]");
    const submitEl = formEl.querySelector("a.s_website_form_send");
    expect(nameEl).not.toBe(undefined);
    expect(nameEl.value).toBe("Mitchell Admin");
    expect(mailEl).not.toBe(undefined);
    expect(mailEl.value).toBe("");
    expect(subjectEl).not.toBe(undefined);
    expect(questionEl).not.toBe(undefined);
    expect(submitEl).not.toBe(undefined);
});

test("(name) form checks conditions", async () => {
    const { el } = await startInteractions(formTemplate);
    const nameEl = el.querySelector("input[name=name]");

    const checkField = (isVisible, hasError) => {
        const fieldEl = field(nameEl);
        isVisible ? expect(fieldEl).not.toHaveClass("d-none") : expect(fieldEl).toHaveClass("d-none");
        isVisible ? expect(nameEl.disabled).not.toBe(undefined) : expect(nameEl.disabled).toBe(true);
        hasError ? expect(nameEl).toHaveClass("is-invalid") : expect(nameEl).not.toHaveClass("is-invalid");
        hasError ? expect(fieldEl).toHaveClass("o_has_error") : expect(fieldEl).not.toHaveClass("o_has_error");
    };

    checkField(true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, false);
    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, false);
    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, false);
    // Fill question
    await click("textarea[name=description]");
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkField(true, false);
    // Submit
    onRpc("/website/form/mail.mail", async () => { return {} });
    await click("a.s_website_form_send");
    checkField(true, false);
});

test("(mail) form checks conditions", async () => {
    const { el } = await startInteractions(formTemplate);
    const mailEl = el.querySelector("input[name=email_from]");

    const checkField = (isVisible, hasError) => {
        const fieldEl = field(mailEl);
        isVisible ? expect(fieldEl).not.toHaveClass("d-none") : expect(fieldEl).toHaveClass("d-none");
        isVisible ? expect(mailEl.disabled).not.toBe(undefined) : expect(mailEl.disabled).toBe(true);
        hasError ? expect(mailEl).toHaveClass("is-invalid") : expect(mailEl).not.toHaveClass("is-invalid");
        hasError ? expect(fieldEl).toHaveClass("o_has_error") : expect(fieldEl).not.toHaveClass("o_has_error");
    };

    checkField(true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, true);
    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(true, true);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, false);
    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, false);
    // Fill question
    await click("textarea[name=description]");
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkField(true, false);
    // Submit
    onRpc("/website/form/mail.mail", async () => { return {} });
    await click("a.s_website_form_send");
    checkField(true, false);
});

test("(subject) form checks conditions", async () => {
    const { el } = await startInteractions(formTemplate);
    const subjectEl = el.querySelector("input[name=subject]");

    const checkField = (isVisible, hasError) => {
        const fieldEl = field(subjectEl);
        isVisible ? expect(fieldEl).not.toHaveClass("d-none") : expect(fieldEl).toHaveClass("d-none");
        isVisible ? expect(subjectEl.disabled).not.toBe(undefined) : expect(subjectEl.disabled).toBe(true);
        hasError ? expect(subjectEl).toHaveClass("is-invalid") : expect(subjectEl).not.toHaveClass("is-invalid");
        hasError ? expect(fieldEl).toHaveClass("o_has_error") : expect(fieldEl).not.toHaveClass("o_has_error");
    };

    checkField(false, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(false, false);
    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, true);
    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(true, true);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, false);
    // Fill question
    await click("textarea[name=description]");
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkField(true, false);
    // Submit
    onRpc("/website/form/mail.mail", async () => { return {} });
    await click("a.s_website_form_send");
    checkField(true, false);
});

test("(question) form checks conditions", async () => {
    const { el } = await startInteractions(formTemplate);
    const questionEl = el.querySelector("textarea[name=description]");

    const checkField = (isVisible, hasError) => {
        const fieldEl = field(questionEl);
        isVisible ? expect(fieldEl).not.toHaveClass("d-none") : expect(fieldEl).toHaveClass("d-none");
        isVisible ? expect(questionEl.disabled).not.toBe(undefined) : expect(questionEl.disabled).toBe(true);
        hasError ? expect(questionEl).toHaveClass("is-invalid") : expect(questionEl).not.toHaveClass("is-invalid");
        hasError ? expect(fieldEl).toHaveClass("o_has_error") : expect(fieldEl).not.toHaveClass("o_has_error");
    };

    checkField(false, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(false, false);
    // Fill mail
    await click("input[name=email_from]");
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkField(false, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(false, false);
    // Fill subject
    await click("input[name=subject]");
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkField(true, false);
    // Submit
    await click("a.s_website_form_send");
    checkField(true, true);
    // Fill question
    await click("textarea[name=description]");
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkField(true, true);
    // Submit
    onRpc("/website/form/mail.mail", async () => { return {} });
    await click("a.s_website_form_send");
    checkField(true, false);
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

test("form prefilled conditional", async () => {
    patchWithCleanup(MockServer.prototype, {
        callOrm(params) {
            expect(params.model).toBe("res.users");
            expect(params.method).toBe("read");
            const result = super.callOrm(...arguments);
            result[0].phone = "+1-555-5555";
            return result;
        }
    });

    // Phone number is only visible if name is filled.
    const { core, el } = await startInteractions(`
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
    expect(core.interactions.length).toBe(1);
    const formEl = el.querySelector("form");
    const nameEl = formEl.querySelector("input[name=name]");
    const phoneEl = formEl.querySelector("input[name=phone]");

    expect(nameEl).not.toBe(undefined);
    expect(nameEl.value).toBe("Mitchell Admin");
    expect(phoneEl).not.toBe(undefined);
    expect(phoneEl.value).toBe("+1-555-5555");
});
