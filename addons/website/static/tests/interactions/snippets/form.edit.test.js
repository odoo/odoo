import { describe, expect, test } from "@odoo/hoot";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { onRpc } from "@web/../tests/web_test_helpers";
import { switchToEditMode } from "../../helpers";

setupInteractionWhiteList("website.form");

describe.current.tags("interaction_dev");

const formXml = `
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
                        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_custom o_draggable" data-type="char">
                            <div class="row s_col_no_resize s_col_no_bgcolor">
                                <label class="col-form-label col-sm-auto s_website_form_label" style="width: 200px" for="o291di1too2s">
                                    <span class="s_website_form_label_content">Company</span>
                                </label>
                                <div class="col-sm">
                                    <input class="form-control s_website_form_input" type="text" name="company" data-fill-with="commercial_company_name" id="o291di1too2s"/>
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

function setupUser() {
    onRpc("res.users", "read", ({ parent }) => {
        const result = parent();
        result[0].commercial_company_name = "TestCompany";
        return result;
    });
}

test("form formats date in edit mode", async () => {
    const { core } = await startInteractions(formXml, { waitForStart: true, editMode: true });
    await switchToEditMode(core);
    expect(core.interactions).toHaveLength(1);
    expect("form input[name=When]").toHaveValue("01/01/2025 10:00:00");
    // Verify that non-edit code did not run.
    expect(".s_website_form_datetime").not.toHaveClass("s_website_form_datepicker_initialized");
});

test("form is NOT prefilled in edit mode", async () => {
    setupUser();
    const { core } = await startInteractions(formXml, { waitForStart: true, editMode: true });
    await switchToEditMode(core);
    expect(core.interactions).toHaveLength(1);
    expect("form input[name=company]").toHaveValue("");
});

test("form is NOT prefilled in translate mode", async () => {
    setupUser();
    const { core } = await startInteractions(formXml, { waitForStart: true, translateMode: true });
    expect(core.interactions).toHaveLength(1);
    expect("form input[name=company]").toHaveValue("");
});
