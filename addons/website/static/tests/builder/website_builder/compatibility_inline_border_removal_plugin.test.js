import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("compatibility inline border removal plugin", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="row">
                <div class="test" style="border-radius: 10px;">Test Compatibility Inline Border Removal plugin</div>
            </div>
        </section>
    `);

    // Add border-width
    await contains(":iframe section .row > div").click();
    expect("[data-action-param*='--box-border-radius'] input").toHaveValue("10");
    await contains("[data-action-param*='--box-border-width'] input").edit("1");

    // Check that border-radius has changed correctly
    expect(":iframe .test").not.toHaveAttribute("style", "border-radius: 10px;");
    expect(":iframe .test").toHaveAttribute(
        "style",
        "--box-border-bottom-left-radius: 10px; --box-border-bottom-right-radius: 10px; --box-border-top-right-radius: 10px; --box-border-top-left-radius: 10px; --box-border-left-width: 1px; --box-border-bottom-width: 1px; --box-border-right-width: 1px; --box-border-top-width: 1px;"
    );
});
