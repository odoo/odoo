import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { advanceTime, Deferred } from "@odoo/hoot-mock";
import { MockServer, onRpc, patchWithCleanup, webModels } from "@web/../tests/web_test_helpers";
import {
    startInteractions,
    setupInteractionWhiteList,
} from "../../core/helpers";

setupInteractionWhiteList("website.form");

test("form formats date in edit mode", async () => {
    const { core, el } = await startInteractions(`
        <div id="wrapwrap">
            <section class="s_website_form pt16 pb16" data-vcss="001" data-snippet="s_website_form" data-name="Form">
                <div class="container-fluid">
                    <form action="/website/form/" method="post" enctype="multipart/form-data" class="o_mark_required" data-mark="*" data-pre-fill="true" data-model_name="mail.mail" data-success-mode="redirect" data-success-page="/contactus-thank-you">
                        <div class="s_website_form_rows row s_col_no_bgcolor">
                            <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom o_draggable" data-type="datetime">
                                <div class="row s_col_no_resize s_col_no_bgcolor">
                                    <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="onbni9ji3oa">
                                        <span class="s_website_form_label_content">When ?</span>
                                    </label>
                                    <div class="col-sm">
                                        <div class="s_website_form_datetime input-group date">
                                            <input type="text" class="form-control datetimepicker-input s_website_form_input" name="When" placeholder="" id="onbni9ji3oa" value="1735722000"/>
                                            <div class="input-group-text o_input_group_date_icon">
                                                <i class="fa fa-calendar"/>
                                            </div>
                                        </div>
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
    `, { editMode: true });
    expect(core.interactions.length).toBe(1);
    const formEl = el.querySelector("form");
    const dateEl = el.querySelector("input[name=When]");
    expect(dateEl.value).toBe("01/01/2025 10:00:00");
    // Verify that non-edit code did not run.
    const dateField = dateEl.closest(".s_website_form_datetime");
    expect(dateField).not.toHaveClass("s_website_form_datepicker_initialized");
});
