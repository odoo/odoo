import { expect, test, waitFor } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("'Show Header' and 'Show Footer' toggle their view, tooltips follow the state", async () => {
    onRpc("/website/theme_customize_data_get", () => ["website.option_layout_hide_footer"]);
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step({ enable: params.enable, disable: params.disable });
    });
    await setupWebsiteBuilder(`<div class="test">b</div>`);
    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await waitFor(".o_theme_tab");

    const headerRow = "div.o_hb_row:contains(Show Header)";
    const footerRow = "div.o_hb_row:contains(Show Footer)";
    expect(`${headerRow} input[type=checkbox]`).toBeChecked();
    expect(`${headerRow} [data-tooltip]`).toHaveAttribute(
        "data-tooltip",
        "Hide header on all pages"
    );
    expect(`${footerRow} input[type=checkbox]`).not.toBeChecked();
    expect(`${footerRow} [data-tooltip]`).toHaveAttribute(
        "data-tooltip",
        "Show footer on all pages"
    );

    await contains(`${headerRow} input[type=checkbox]`).click();
    await expect.waitForSteps([{ enable: ["website.option_layout_hide_header"], disable: [] }]);
});
