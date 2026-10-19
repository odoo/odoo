import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("changing border width preserves inline border radius", async () => {
    await setupWebsiteBuilder(
        `
        <section>
            <div class="row">
                <div class="test" style="border-width: 4px; border-radius: 16px; border-style: solid;">
                    Test Compatibility Inline Border Removal plugin
                </div>
            </div>
        </section>
        `,
        { loadIframeBundles: true }
    );

    await contains(":iframe section .row > div").click();
    expect("[data-action-param*='--box-border-width'] input").toHaveValue("4");
    expect("[data-action-param*='--box-border-radius'] input").toHaveValue("16");

    await contains("[data-action-param*='--box-border-width'] input").edit("8");
    expect("[data-action-param*='--box-border-radius'] input").toHaveValue("16");
    expect(":iframe .test").toHaveStyle({ "border-width": "8px", "border-radius": "16px" });
});

test("changing border radius preserves inline border width", async () => {
    await setupWebsiteBuilder(
        `
        <section>
            <div class="row">
                <div class="test" style="border-width: 4px; border-radius: 16px; border-style: solid;">
                    Test Compatibility Inline Border Removal plugin
                </div>
            </div>
        </section>
        `,
        { loadIframeBundles: true }
    );

    await contains(":iframe section .row > div").click();
    expect("[data-action-param*='--box-border-width'] input").toHaveValue("4");
    expect("[data-action-param*='--box-border-radius'] input").toHaveValue("16");

    await contains("[data-action-param*='--box-border-radius'] input").edit("24");
    expect("[data-action-param*='--box-border-width'] input").toHaveValue("4");
    expect(":iframe .test").toHaveStyle({ "border-width": "4px", "border-radius": "24px" });
});
