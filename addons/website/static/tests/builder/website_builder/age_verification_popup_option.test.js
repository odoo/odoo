import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Age verification popup options works correctly", async () => {
    await setupWebsiteBuilderWithSnippet("s_age_verification_popup", {
        loadIframeBundles: true,
        loadAssetsFrontendJS: true,
    });
    await contains(":iframe .s_age_verification_popup .modal").click();
    expect("[data-label='Display']").toHaveCount(0);
    expect("[data-label='Delay']").toHaveCount(0);
    expect("[data-label='Confirmation'] .dropdown-toggle").toHaveText("Yes or No");
    expect(":iframe #age_confirmation_block .o_age_verification_yes_btn").toHaveCount(1);
    expect("[data-label='Minimum Age']").toHaveCount(0);

    await contains("[data-label='Confirmation'] .dropdown-toggle").click();
    await contains(".o-dropdown-item:contains('Birth Year')").click();
    expect(":iframe .o_age_verify_year_btn.oe_unremovable").toHaveCount(1);
    expect("[data-label='Minimum Age'] input").toHaveValue(18);

    await contains("[data-label='Minimum Age'] input").edit("20");
    expect(":iframe .s_age_verification_popup .modal[data-min-age='20']").toHaveCount(1);

    await contains("[data-label='Confirmation'] .dropdown-toggle").click();
    await contains(".o-dropdown-item:contains('Birth Date')").click();
    expect(":iframe .o_age_verification_birth_date").toHaveCount(1);
    expect(":iframe .o_age_verify_date_btn.oe_unremovable").toHaveCount(1);
    expect("[data-label='Minimum Age'] input").toHaveCount(1);

    expect(":iframe #verification_error").not.toBeVisible();
    await contains(".fa-eye-slash[data-class-action='d-none']").click();
    expect(":iframe #verification_error").toBeVisible();
});
