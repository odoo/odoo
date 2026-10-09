import { expect, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const HIDE_EMPTY_CART = "website_sale.header_hide_empty_cart_link";

test("'Show Empty' renders the header without a reload, written on save", async () => {
    onRpc("/website/theme_customize_data_get", () => [HIDE_EMPTY_CART]);
    onRpc("/blank", (request) => {
        const views = JSON.parse(new URL(request.url).searchParams.get("theme_preview_views"));
        expect.step(`render ${JSON.stringify(views)}`);
        const cart = views[HIDE_EMPTY_CART] === false ? `<a class="o_wsale_my_cart">Cart</a>` : "";
        return new Response(
            `<html><body><div id="wrapwrap"><header id="top">Header${cart}</header><main></main></div></body></html>`
        );
    });
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`write ${JSON.stringify(params.disable)}`);
    });
    await setupWebsiteBuilder("", {
        headerContent: `<header id="top">Header</header><main></main>`,
    });
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Show Empty'] .o_btn_show_empty_cart").click();
    await waitFor(":iframe header#top .o_wsale_my_cart");
    await waitFor("[data-label='Show Empty'] .o_btn_show_empty_cart.active");
    expect.verifySteps(["render {}", `render {"${HIDE_EMPTY_CART}":false}`]);
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps([`write ["${HIDE_EMPTY_CART}"]`]);
});
