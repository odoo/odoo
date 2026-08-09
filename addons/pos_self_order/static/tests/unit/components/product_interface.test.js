import { test, expect } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { Component, useProps, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductInterface } from "@pos_self_order/app/components/product_interface/product_interface";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

/**
 * Minimal host for ProductInterface, standing in for a real page (product, combo,
 * optional product) so the shared layout can be tested on its own.
 */
class TestPage extends Component {
    static components = { ProductInterface };
    static template = xml`
        <ProductInterface
            class="'o_self_test_page'"
            productTemplate="this.props.productTemplate"
            goBack.bind="this.goBack">
            <t t-set-slot="content">
                <div class="o_self_test_content">Page content</div>
            </t>
            <t t-set-slot="scroll-end-content">
                <div class="o_self_test_scroll_end">Scroll end</div>
            </t>
            <t t-set-slot="footer">
                <button class="btn o_self_test_footer_btn">Footer action</button>
            </t>
        </ProductInterface>`;

    props = useProps();
    goBackCalls = 0;

    goBack() {
        this.goBackCalls++;
    }
}

const mountInterface = async (productId = 5) => {
    const store = await setupSelfPosEnv();
    const productTemplate = store.models["product.template"].get(productId);
    const comp = await mountWithCleanup(TestPage, { props: { productTemplate } });
    return { store, comp, productTemplate };
};

test("renders header, content, scroll-end and footer slots around the product", async () => {
    const { productTemplate } = await mountInterface();

    expect(".o_self_product_interface").toHaveCount(1);
    // The `class` prop is forwarded to the layout root, so pages stay addressable.
    expect(".o_self_product_interface").toHaveClass("o_self_test_page");

    expect(".o_self_product_header").toHaveCount(1);
    expect(".o_self_footer").toHaveCount(1);
    expect(".o_self_test_content").toHaveCount(1);
    expect(".o_self_test_scroll_end").toHaveCount(1);
    expect(".o_self_test_footer_btn").toHaveCount(1);

    // Name and image are provided by the layout itself, not by the page.
    expect(".o_self_product_interface h1").toHaveText(productTemplate.name);
    expect(".o_self_product_image img").toHaveCount(1);
});

test("puts the content slots inside the scroll area and the footer outside of it", async () => {
    await mountInterface();

    expect("#o-self-scroll-container .o_self_test_content").toHaveCount(1);
    expect("#o-self-scroll-container .o_self_test_scroll_end").toHaveCount(1);
    expect("#o-self-scroll-container .o_self_test_footer_btn").toHaveCount(0);
    expect(".o_self_footer .o_self_test_footer_btn").toHaveCount(1);
});

test("exposes the scroll container under the id the pages look up", async () => {
    await mountInterface();

    // shouldShowMissingDetails and ComboPage.resetScrollPosition reach the scroll area
    // through this id, so the layout must render exactly one element carrying it.
    expect("#o-self-scroll-container").toHaveCount(1);
    expect(document.getElementById("o-self-scroll-container")).not.toBe(null);
});

test("the header discard button calls the goBack prop", async () => {
    const { comp } = await mountInterface();

    expect(comp.goBackCalls).toBe(0);
    await click(".o_self_product_header button");
    await animationFrame();
    expect(comp.goBackCalls).toBe(1);
});

test("the sticky header title starts hidden and carries the product name", async () => {
    const { productTemplate } = await mountInterface();

    // Big title in the scroll area, sticky copy in the header.
    expect("#o-self-scroll-container h1").toHaveText(productTemplate.name);
    expect(".o_self_product_header .o_self_product_name").toHaveText(productTemplate.name);
    // Hidden until useStickyTitleObserver reports the big title left the viewport.
    expect(".o_self_product_header .o_self_product_name").toHaveClass("d-none");
    expect(".o_self_product_header button span").not.toHaveClass("invisible");
});
