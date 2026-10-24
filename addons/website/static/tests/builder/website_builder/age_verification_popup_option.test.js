import { expect, test } from "@odoo/hoot";
import { setInputRange } from "@odoo/hoot-dom";
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
        loadIframeBuilderTemplates: true,
    });
    const modalSelector = ":iframe .s_age_verification_popup .modal";
    await contains(modalSelector).click();
    expect("[data-label='Display']").toHaveCount(0);
    expect("[data-label='Delay']").toHaveCount(0);
    expect("[data-label='Confirmation'] .dropdown-toggle").toHaveText("Yes or No");
    expect(
        ":iframe #age_confirmation_block .o_age_verification_yes_btn.oe_unremovable"
    ).toHaveCount(1);
    expect(":iframe #age_confirmation_block .o_age_verification_no_btn.oe_unremovable").toHaveCount(
        1
    );
    expect("[data-label='Minimum Age']").toHaveCount(0);

    await contains("[data-label='Confirmation'] .dropdown-toggle").click();
    await contains(".o-dropdown-item:contains('Birth Year')").click();
    expect(":iframe input[name='age_verification_birth_year']").toHaveCount(1);
    expect(":iframe .o_age_verification_year_btn.oe_unremovable").toHaveCount(1);
    expect("[data-label='Minimum Age'] input").toHaveValue(18);

    await contains("[data-label='Confirmation'] .dropdown-toggle").click();
    await contains(".o-dropdown-item:contains('Birth Date')").click();
    expect(":iframe input[name='age_verification_birth_date']").toHaveCount(1);
    expect(":iframe .o_age_verification_date_btn.oe_unremovable").toHaveCount(1);
    expect("[data-label='Minimum Age'] input").toHaveCount(1);

    expect(":iframe #verification_error").not.toBeVisible();
    await contains("[data-class-action='d-none'] [data-icon='visibility_off']").click();
    expect(":iframe #verification_error").toBeVisible();

    const backgroundBlurSelector = "[data-label='Background blur'] input[type='range']";
    expect(modalSelector).toHaveAttribute("data-blur-background", "true");
    expect(backgroundBlurSelector).toHaveValue(16);
    await setInputRange(backgroundBlurSelector, 24);
    expect(modalSelector).toHaveAttribute("data-blur-background", "24");
    expect(":iframe :root").toHaveStyle(
        { "--o-age-popup-background-blur": "24px" },
        { inline: true }
    );
    await setInputRange(backgroundBlurSelector, 0);
    expect(modalSelector).not.toHaveAttribute("data-blur-background");
    expect(":iframe :root").not.toHaveStyle(
        { "--o-age-popup-background-blur": "24px" },
        { inline: true }
    );
});
