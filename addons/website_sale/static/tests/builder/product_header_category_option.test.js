import { expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("saving without toggling a category header option sends no config", async () => {
    // The header classes reflect the settings as they were when the editor loaded, so sending them
    // would overwrite changes made since then, e.g. by the AI before it reloads the editor
    onRpc("/shop/config/website", () => expect.step("config"));
    const { getEditor } = await setupWebsiteBuilder(`
        <div id="products_grid">
            <header
                id="o_wsale_products_header"
                class="o_wsale_products_header_is_category
                    o_wsale_products_header_show_category_description"
            >
                <h1 class="o_wsale_category_title">Desks</h1>
            </header>
        </div>
    `);
    await getEditor().shared.savePlugin.save();
    expect.verifySteps([]);
});

test("saving after toggling a category header option sends the new config", async () => {
    onRpc("ir.ui.view", "save", () => true);
    onRpc("/shop/config/website", async (request) => {
        const { params } = await request.json();
        expect.step(params);
    });
    const { getEditor } = await setupWebsiteBuilder(`
        <div id="products_grid">
            <header id="o_wsale_products_header" class="o_wsale_products_header_is_category">
                <h1 class="o_wsale_category_title">Desks</h1>
            </header>
        </div>
    `);
    await contains(":iframe .o_wsale_category_title").click();
    await contains("[data-action-id='toggleCategoryShowTitle'] input").click();
    await getEditor().shared.savePlugin.save();
    expect.verifySteps([
        {
            show_category_title: true,
            show_category_description: false,
            align_category_content: false,
        },
    ]);
});
