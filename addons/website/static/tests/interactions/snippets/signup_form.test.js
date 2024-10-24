import { expect, press, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const signupFormTemplate = `
    <section class="s_website_form pt40 pb40" data-vcss="001" data-snippet="s_website_form" data-name="Form">
        <div class="o_container_small">
            <form action="/web/signup" method="post" enctype="multipart/form-data" class="oe_signup_form o_mark_required" data-mark="*" data-model_name="res.users" data-success-mode="redirect" data-success-page="/my" data-custom-url-submit="true">
                <div class="s_website_form_rows row s_col_no_bgcolor">
                    ${makeFormField({ type: "char", name: "name", label: "Name", required: true })}
                    ${makeFormField({
                        type: "char",
                        name: "login",
                        label: "Email",
                    })}
                    ${makeFormField({
                        type: "password",
                        name: "password",
                        label: "Password",
                    })}
                    ${makeFormField({
                        type: "password",
                        name: "confirm_password",
                        label: "Confirm Password",
                        extraClasses: "s_website_form_custom",
                    })}
                    <div class="text-center s_website_form_submit d-grid pt-3">
                        <a role="button" class="btn btn-primary s_website_form_send">Sign up</a>
                        <span id="s_website_form_result"/>
                    </div>
                </div>
            </form>
        </div>
    </section>
`;

// Generates a standard form field HTML string.
function makeFormField({ type, name, label, extraClasses = "" }) {
    const inputType = type === "password" ? "password" : "text";
    const extra = extraClasses ? `${extraClasses}` : "";
    return `
        <div data-name="Field" class="s_website_form_field mb-3 col-12 s_website_form_model_required ${extra}" data-type="${type}">
            <div class="row s_col_no_resize s_col_no_bgcolor">
                <label class="col-form-label col-sm-auto s_website_form_label" for="${name}">
                    <span class="s_website_form_label_content">${label}</span>
                    <span class="s_website_form_mark"> *</span>
                </label>
                <div class="col-sm">
                    <input class="form-control s_website_form_input" type="${inputType}" name="${name}" required="required" id="${name}"/>
                </div>
            </div>
        </div>`;
}

async function addNewField() {
    await contains("div[data-container-title='Form'] button.btn-success").click();
}

async function changeFieldType(actionValue) {
    await contains("[data-container-title='Field'] [data-label='Type'] .dropdown-toggle").click();
    await contains(`.o_popover [data-action-value='${actionValue}']`).click();
    await animationFrame();
}

const authorizedFieldsMock = {
    zip: { name: "zip", type: "char", string: "Zip" },
    city: { name: "city", type: "char", string: "City" },
    country_id: {
        name: "country_id",
        type: "many2one",
        relation: "res.country",
        string: "Country",
    },
    company_ids: {
        name: "company_ids",
        type: "many2many",
        relation: "res.company",
        string: "Companies",
    },
};

test("add custom fields to signup form via builder options", async () => {
    onRpc("get_authorized_fields", () => authorizedFieldsMock);
    await setupWebsiteBuilder(signupFormTemplate);

    // Initially only the 4 required fields should be present
    // (name, email, password, confirm password)
    expect(":iframe .s_website_form_field").toHaveCount(4);

    await contains(":iframe input#confirm_password").click();
    const modelFields = [
        { type: "zip", selector: ":iframe .s_website_form_input[name='zip']" },
        { type: "city", selector: ":iframe .s_website_form_input[name='city']" },
        { type: "country_id", selector: ":iframe .s_website_form_input[name='country_id']" },
        { type: "company_ids", selector: ":iframe [name='company_ids']" },
    ];
    for (const { type, selector } of modelFields) {
        await addNewField();
        await changeFieldType(type);
        expect(selector).toHaveCount(1);
    }

    // Add a binary field and check that it is properly rendered in the form
    // with the correct label
    await addNewField();
    await changeFieldType("binary");
    await contains("[data-action-id='setLabelText'] input").edit("file_1");
    await press("Tab");
    expect(":iframe span.s_website_form_label_content:contains('file_1')").toHaveCount(1);

    // Add a char field and check that it is properly rendered in the form with
    // the correct label
    await addNewField();
    await contains("[data-action-id='setLabelText'] input").edit("field_1");
    await press("Tab");
    expect(":iframe span.s_website_form_label_content:contains('field_1')").toHaveCount(1);

    // In total we should have the 4 required fields + the 4 model fields + the
    // 2 custom fields = 10 fields
    expect(":iframe .s_website_form_field").toHaveCount(10);
});
