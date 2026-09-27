import { test, expect } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { Component, proxy, xml } from "@odoo/owl";
import { findComponent, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

/**
 * Mount a single ProductCard through a parent component. Props only update through a
 * parent re-render, so the card gets its props from a reactive object the test can
 * mutate: one mounted card is enough to go through every prop combination.
 *
 * @returns {{ card: ProductCard, setProps: (props: object) => Promise<void> }}
 */
const mountProductCard = async (store, cardProps) => {
    store.computeAvailableCategories();
    const props = proxy(cardProps);

    class Wrapper extends Component {
        static template = xml`<ProductCard t-props="this.cardProps"/>`;
        static components = { ProductCard };
        setup() {
            this.cardProps = props;
        }
    }

    const wrapper = await mountWithCleanup(Wrapper);
    return {
        card: findComponent(wrapper, (c) => c instanceof ProductCard),
        setProps: async (newProps) => {
            Object.assign(props, newProps);
            await animationFrame();
        },
    };
};

test("card content", async () => {
    const store = await setupSelfPosEnv();
    const product = store.models["product.template"].get(5);
    const { setProps } = await mountProductCard(store, {
        product,
        class: "o_self_test_card",
        hidePrice: false,
        qty: 0,
    });

    // Name, image and price are rendered, the class prop reaches the card root, and a
    // zero qty gets no badge. No description nor tags means no info icon either.
    expect(".o_self_product_card").toHaveCount(1);
    expect(".o_self_product_card").toHaveClass("o_self_test_card");
    expect(".self_order_product_name span").toHaveText(product.name);
    // Hoot serves a placeholder for images, so only the element itself is asserted.
    expect(".o_self_product_card_img").toHaveCount(1);
    expect(".o-so-tabular-nums").toHaveCount(1);
    expect(".o_self_product_card .badge").toHaveCount(0);
    expect(".product_info_icon").toHaveCount(0);

    // hidePrice drops the price, as the combo page needs.
    await setProps({ hidePrice: true });
    expect(".o-so-tabular-nums").toHaveCount(0);

    // Only a positive qty renders a badge.
    await setProps({ hidePrice: false, qty: 3 });
    expect(".o_self_product_card .badge").toHaveText("3");

    // A description brings the info icon in.
    product.public_description = "<p>A tasty description</p>";
    await animationFrame();
    expect(".product_info_icon").toHaveCount(1);
});

test("a snoozed product is dimmed and cannot be added to the cart", async () => {
    const store = await setupSelfPosEnv();
    const product = store.models["product.template"].get(5);
    patchWithCleanup(store, { isProductSnoozed: () => true });
    await mountProductCard(store, { product });

    expect(".o_self_product_card").toHaveClass("opacity-25");
    expect(".o_self_product_card .badge").toHaveText("Out of stock");

    await click(".o_self_product_card");
    await animationFrame();
    expect(store.currentOrder.lines).toHaveLength(0);
});

test("selectProduct", async () => {
    const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
    const models = store.models;
    const product = models["product.template"].get(5);
    const selected = [];
    const { card, setProps } = await mountProductCard(store, {
        product,
        selectProduct: (p) => selected.push(p.id),
    });

    // The selectProduct prop replaces the default handler, nothing reaches the cart.
    await click(".o_self_product_card");
    await animationFrame();
    expect(selected).toEqual([5]);
    expect(store.currentOrder.lines).toHaveLength(0);

    // Without the override, the product is added to the cart.
    await setProps({ selectProduct: undefined });
    card.selectProduct();
    expect(store.currentOrder.lines).toHaveLength(1);
    expect(store.currentOrder.lines[0].product_id.id).toBe(5);

    // Once every combo is down to a single item, there is nothing left to choose: the
    // combo skips the selection page and goes straight to the cart.
    const comboProduct = models["product.template"].get(7);
    [1, 2].forEach((comboId) => {
        const productCombo = store.models["product.combo"].get(comboId);
        productCombo.combo_item_ids = [productCombo.combo_item_ids[0]];
        productCombo.qty_max = 1;
    });
    await setProps({ product: comboProduct });
    card.selectProduct();
    expect(store.currentOrder.lines).toHaveLength(4);

    // A combo product leaving something to choose sends the customer to the combo
    // selection page, so the cart is left untouched.
    store.models["product.combo"].get(1).combo_item_ids = [1, 2];
    card.selectProduct();
    expect(store.currentOrder.lines).toHaveLength(4);
});
