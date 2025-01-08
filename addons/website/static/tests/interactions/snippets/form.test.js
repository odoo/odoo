import { describe, expect, test } from "@odoo/hoot";
import { click, fill } from "@odoo/hoot-dom";
import { advanceTime, Deferred } from "@odoo/hoot-mock";
import { MockServer, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.form", "website.post_link");
describe.current.tags("interaction_dev");

function field(inputEl) {
    return inputEl.closest(".s_website_form_field");
}

// TODO Split in distinct tests.

test("form checks conditions", async () => {
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
    `);
    expect(core.interactions.length).toBe(1);
    const formEl = el.querySelector("form");
    const nameEl = formEl.querySelector("input[name=name]");
    const mailEl = formEl.querySelector("input[name=email_from]");
    const subjectEl = formEl.querySelector("input[name=subject]");
    const questionEl = formEl.querySelector("textarea[name=description]");
    const submitEl = formEl.querySelector("a.s_website_form_send");

    function checkVisibility(
        isNameVisible,
        isMailVisible,
        isSubjectVisible,
        isQuestionVisible,
    ) {
        function checkSingle(isVisible, el) {
            const fieldEl = field(el);
            if (isVisible) {
                expect(fieldEl).not.toHaveClass("d-none");
                expect(el.disabled).not.toBe(undefined);
            } else {
                expect(fieldEl).toHaveClass("d-none");
                expect(el.disabled).toBe(true);
            }
        }
        checkSingle(isNameVisible, nameEl);
        checkSingle(isMailVisible, mailEl);
        checkSingle(isSubjectVisible, subjectEl);
        checkSingle(isQuestionVisible, questionEl);
    }
    function checkError(
        hasNameError,
        hasMailError,
        hasSubjectError,
        hasQuestionError,
    ) {
        function checkSingle(hasError, el) {
            const fieldEl = field(el);
            if (hasError) {
                expect(el).toHaveClass("is-invalid");
                expect(fieldEl).toHaveClass("o_has_error");
            } else {
                expect(el).not.toHaveClass("is-invalid");
                expect(fieldEl).not.toHaveClass("o_has_error");
            }
        }
        checkSingle(hasNameError, nameEl);
        checkSingle(hasMailError, mailEl);
        checkSingle(hasSubjectError, subjectEl);
        checkSingle(hasQuestionError, questionEl);
    }
    expect(nameEl).not.toBe(undefined);
    expect(nameEl.value).toBe("Mitchell Admin");
    expect(mailEl).not.toBe(undefined);
    expect(mailEl.value).toBe("");
    expect(subjectEl).not.toBe(undefined);
    expect(questionEl).not.toBe(undefined);
    expect(submitEl).not.toBe(undefined);
    checkVisibility(true, true, false, false);
    checkError(false, false, false, false);
    // Submit => same visibility, error on mail.
    await click(submitEl);
    checkVisibility(true, true, false, false);
    checkError(false, true, false, false);
    // Fill mail => subject becomes visible.
    await click(mailEl);
    await fill("a@b.com");
    await advanceTime(400); // Debounce delay.
    checkVisibility(true, true, true, false);
    checkError(false, true, false, false);
    // Submit => same visibility, error on subject.
    await click(submitEl);
    checkVisibility(true, true, true, false);
    checkError(false, false, true, false);
    // Fill subject => question becomes visible.
    await click(subjectEl);
    await fill("Subject");
    await advanceTime(400); // Debounce delay.
    checkVisibility(true, true, true, true);
    checkError(false, false, true, false);
    // Submit => same visibility, error on question.
    await click(submitEl);
    checkVisibility(true, true, true, true);
    checkError(false, false, false, true);
    // Fill question.
    await click(questionEl);
    await fill("Question");
    await advanceTime(400); // Debounce delay.
    checkVisibility(true, true, true, true);
    checkError(false, false, false, true);
    // Submit => no error & RPC.
    let didRpc = false;
    const rpcDone = new Deferred();
    onRpc("/website/form/mail.mail", async (args) => {
        didRpc = true;
        rpcDone.resolve();
        return {};
    });
    await click(submitEl);
    await rpcDone;
    checkVisibility(true, true, true, true);
    checkError(false, false, false, false);
    expect(didRpc).toBe(true);
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
