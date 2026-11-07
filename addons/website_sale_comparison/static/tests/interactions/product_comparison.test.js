import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { cookie } from "@web/core/browser/cookie";
import { onRpc } from "@web/../tests/web_test_helpers";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website_sale_comparison.product_comparison");
describe.current.tags("interaction_dev");

async function startComparison() {
    cookie.set("comparison_product_ids", "[1]");
    onRpc("/shop/compare/get_product_data", async (request) => {
        const { params } = await request.json();
        expect.step(`load:${params.product_ids.join(",")}`);
        return params.product_ids.map((id) => ({
            id,
            display_name: `Product ${id}`,
            website_url: `/shop/${id}`,
            image_url: "/web/static/img/placeholder.png",
            price: 10,
            currency_id: 1,
            prevent_zero_price_sale: false,
        }));
    });
    await startInteractions(`
        <div class="js_sale">
            <button class="o_add_compare" data-action="o_comparelist"
                data-product-product-id="1" disabled="disabled">Compare product 1</button>
            <button class="o_add_compare" data-action="o_comparelist"
                data-product-product-id="2">Compare product 2</button>
            <button class="o_add_compare_dyn" data-action="o_comparelist"
                data-product-product-id="2">Compare selected variant</button>
        </div>
    `);
    await animationFrame();
}

test("refresh comparison and buttons when restoring a cached page", async () => {
    await startComparison();
    expect(".o_wsale_compare_btn .badge").toHaveText("1");
    expect('[data-product-product-id="1"]').not.toBeEnabled();
    expect('.o_add_compare[data-product-product-id="2"]').toBeEnabled();

    // Another page adds a product while this page remains in the browser's cache.
    cookie.set("comparison_product_ids", "[1,2]");
    window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
    await animationFrame();
    expect(".o_wsale_compare_btn .badge").toHaveText("2");
    expect('.o_add_compare[data-product-product-id="2"]').not.toBeEnabled();
    expect(".o_add_compare_dyn").not.toBeEnabled();

    // A product removed on another page must also disappear after restoration.
    cookie.set("comparison_product_ids", "[2]");
    window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
    await animationFrame();
    expect(".o_wsale_compare_btn .badge").toHaveText("1");
    expect('[data-product-product-id="1"]').toBeEnabled();
    expect('.o_add_compare[data-product-product-id="2"]').not.toBeEnabled();

    cookie.set("comparison_product_ids", "[]");
    window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: true }));
    await animationFrame();
    expect(".o_wsale_comparison_bottom_bar").toHaveCount(0);
    expect('[data-product-product-id="1"]').toBeEnabled();
    expect('.o_add_compare[data-product-product-id="2"]').toBeEnabled();
    expect(".o_add_compare_dyn").toBeEnabled();
    expect.verifySteps(["load:1", "load:1,2", "load:2"]);
});

test("ordinary pageshow does not reload the comparison", async () => {
    await startComparison();
    cookie.set("comparison_product_ids", "[1,2]");
    window.dispatchEvent(new PageTransitionEvent("pageshow", { persisted: false }));
    await animationFrame();
    expect(".o_wsale_compare_btn .badge").toHaveText("1");
    expect('.o_add_compare[data-product-product-id="2"]').toBeEnabled();
    expect.verifySteps(["load:1"]);
});
