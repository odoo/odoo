import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("website border configurator", async () => {
    await setupWebsiteBuilder(`
        <section>
            <div class="row">
                <div class="test">Test website border configurator</div>
            </div>
        </section>
    `);

    expect(":iframe .test").not.toHaveAttribute("style");

    // Adding a custom radius adds the corresponding CSS variable
    await contains(":iframe section .row > div").click();
    await contains("[data-action-param*='--box-border-radius'] input").edit("1");
    expect(":iframe .test").toHaveAttribute(
        "style",
        "--box-border-bottom-left-radius: 1px; --box-border-bottom-right-radius: 1px; --box-border-top-right-radius: 1px; --box-border-top-left-radius: 1px;"
    );

    // Clicking on a preset radius value removes the CSS variable
    await contains(".hb-row-label:contains('Round Corners') + .hb-row-content input").click();
    await contains(".o_popover [role='menuitem']:contains('Large')").click();
    expect(":iframe .test").toHaveAttribute("style", "");
});
