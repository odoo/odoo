import { afterEach, Deferred, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import {
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";

definePosModels();

const pristineConfigs = PosConfig._records;
afterEach(() => {
    PosConfig._records = pristineConfigs;
});

const configureStock = (values) => {
    PosConfig._records = PosConfig._records.map((record) => ({ ...record, ...values }));
};

async function mountCard(product, props = {}) {
    return mountWithCleanup(ProductCard, {
        props: {
            product,
            name: product.display_name,
            productId: product.id,
            imageUrl: false,
            ...props,
        },
    });
}

test("a grouped negative cart quantity keeps its refund styling", async () => {
    const store = await setupPosEnv();
    const product = store.models["product.template"].get(5);
    await mountWithCleanup(ProductCard, {
        props: {
            product,
            name: product.display_name,
            productId: product.id,
            imageUrl: false,
            productCartQty: -1000,
        },
    });
    expect(".product-cart-qty").toHaveText("-1,000");
    expect(".product-cart-qty").toHaveClass("text-danger");
    const reference = document.createElement("span");
    reference.className = "text-danger";
    getFixture().append(reference);
    const badge = getFixture().querySelector(".product-cart-qty");
    expect(getComputedStyle(badge).color).toBe(getComputedStyle(reference).color);
});

for (const quantity of [-0.5, 0.5]) {
    test(`comma-decimal quantity ${quantity} uses its numeric sign for styling`, async () => {
        const store = await setupPosEnv();
        patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });
        const product = store.models["product.template"].get(5);
        await mountWithCleanup(ProductCard, {
            props: {
                product,
                name: product.display_name,
                productId: product.id,
                imageUrl: false,
                productCartQty: quantity,
            },
        });
        expect(".product-cart-qty").toHaveText(quantity < 0 ? "-0,5" : "0,5");
        expect(".product-cart-qty.text-danger").toHaveCount(quantity < 0 ? 1 : 0);
        const reference = document.createElement("span");
        reference.className = quantity < 0 ? "text-danger" : "text-white";
        getFixture().append(reference);
        const badge = getFixture().querySelector(".product-cart-qty");
        expect(getComputedStyle(badge).color).toBe(getComputedStyle(reference).color);
    });
}

test("requests issued in one tick travel as one batched call", async () => {
    const calls = [];
    onRpc("product.product", "get_pos_stock_quantities", ({ args }) => {
        calls.push(args);
        return { 5: 4, 6: 30 };
    });
    await setupPosEnv();
    const service = getService("pos_stock");
    service.request([5]);
    service.request([6, 5]);
    await animationFrame();

    expect(calls).toEqual([[[5, 6], 1]]);
    expect(service.quantities).toEqual({ 5: 4, 6: 30 });
});

test("a reused card requests stock for its new product", async () => {
    onRpc("product.product", "get_pos_stock_quantities", ({ args }) => {
        expect.step(`stock ${args[0].join(",")}`);
        return { 5: 4, 6: 30 };
    });
    const store = await setupPosEnv();
    class Catalog extends Component {
        static props = {};
        static components = { ProductCard };
        static template = xml`<ProductCard product="state.product" productId="state.product.id"
            name="state.product.display_name" imageUrl="false"/>`;
        setup() {
            this.state = useState({ product: store.models["product.template"].get(5) });
        }
    }
    const catalog = await mountWithCleanup(Catalog);
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveText("4");
    expect.verifySteps(["stock 5"]);
    catalog.state.product = store.models["product.template"].get(6);
    await animationFrame();
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveText("30");
    expect.verifySteps(["stock 6"]);
});

test("an old product's late stock response cannot replace the reused card's stock", async () => {
    const oldStock = new Deferred();
    onRpc("product.product", "get_pos_stock_quantities", ({ args }) =>
        args[0].includes(5) ? oldStock : { 6: 30 },
    );
    const store = await setupPosEnv();
    class Catalog extends Component {
        static props = {};
        static components = { ProductCard };
        static template = xml`<ProductCard product="state.product" productId="state.product.id"
            name="state.product.display_name" imageUrl="false"/>`;
        setup() {
            this.state = useState({ product: store.models["product.template"].get(5) });
        }
    }
    const catalog = await mountWithCleanup(Catalog);
    expect(".o_pos_stock_badge").toHaveText("…");
    catalog.state.product = store.models["product.template"].get(6);
    await animationFrame();
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveText("30");
    oldStock.resolve({ 5: 4 });
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveText("30");
});

test("adding a variant to a mounted template requests only its missing stock", async () => {
    onRpc("product.product", "get_pos_stock_quantities", ({ args }) => {
        expect.step(`stock ${args[0].join(",")}`);
        return { 5: 4, 60: 30 };
    });
    const store = await setupPosEnv();
    const template = store.models["product.template"].get(5);
    await mountCard(template);
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveText("4");
    expect.verifySteps(["stock 5"]);
    store.models["product.product"].create({
        id: 60,
        product_tmpl_id: template,
        display_name: "New variant",
    });
    await animationFrame();
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveText("34");
    expect.verifySteps(["stock 60"]);
});

test("enabling stock display after mounting requests quantities", async () => {
    configureStock({ show_stock_in_pos: false });
    onRpc("product.product", "get_pos_stock_quantities", () => {
        expect.step("stock");
        return { 5: 4 };
    });
    const store = await setupPosEnv();
    await mountCard(store.models["product.template"].get(5));
    expect.verifySteps([]);
    store.config.show_stock_in_pos = true;
    await animationFrame();
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveText("4");
    expect.verifySteps(["stock"]);
    store.config.show_stock_in_pos = false;
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveCount(0);
    expect.verifySteps([]);
});

test("mounting a catalog batches requests and unrelated prop changes do not refetch", async () => {
    const calls = [];
    onRpc("product.product", "get_pos_stock_quantities", ({ args }) => {
        calls.push([...args[0]].sort((a, b) => a - b));
        return { 5: 4, 6: 30 };
    });
    const store = await setupPosEnv();
    class Catalog extends Component {
        static props = {};
        static components = { ProductCard };
        static template = xml`<div><ProductCard t-foreach="products" t-as="product" t-key="product.id"
            product="product" productId="product.id" name="product.display_name"
            productCartQty="state.quantity" imageUrl="false"/></div>`;
        setup() {
            this.state = useState({ quantity: 1 });
            this.products = [5, 6].map((id) =>
                store.models["product.template"].get(id),
            );
        }
    }
    const catalog = await mountWithCleanup(Catalog);
    await animationFrame();
    expect(calls).toEqual([[5, 6]]);
    catalog.state.quantity = 2;
    await animationFrame();
    expect(calls).toEqual([[5, 6]]);
});

test("a template card shows its variants' stock, coloured by the threshold", async () => {
    onRpc("product.product", "get_pos_stock_quantities", () => ({ 5: 4, 6: 30 }));
    const store = await setupPosEnv();
    await mountCard(store.models["product.template"].get(5));
    await mountCard(store.models["product.template"].get(6));
    await animationFrame();

    expect(".o_pos_stock_badge").toHaveCount(2);
    expect(".o_pos_stock_low").toHaveText("4");
    expect(".o_pos_stock_available").toHaveText("30");
    expect(".o_pos_stock_badge.top-0.start-0").toHaveCount(2);
});

test("zero stock is red and the position follows the configuration", async () => {
    configureStock({ stock_display_location: "bottom_right" });
    onRpc("product.product", "get_pos_stock_quantities", () => ({ 5: 0 }));
    const store = await setupPosEnv();
    await mountCard(store.models["product.template"].get(5));
    await animationFrame();

    expect(".o_pos_stock_empty.bottom-0.end-0").toHaveText("0");
});

test("a failed fetch marks the card unknown rather than empty", async () => {
    onRpc("product.product", "get_pos_stock_quantities", () => {
        throw new Error("stock is down");
    });
    const store = await setupPosEnv();
    await mountCard(store.models["product.template"].get(5));
    await animationFrame();

    expect(".o_pos_stock_unknown").toHaveText("?");
    expect(".o_pos_stock_empty").toHaveCount(0);
});

test("no badge when the configuration disables the display", async () => {
    configureStock({ show_stock_in_pos: false });
    onRpc("product.product", "get_pos_stock_quantities", () => {
        expect.step("rpc");
        return {};
    });
    const store = await setupPosEnv();
    await mountCard(store.models["product.template"].get(5));
    await animationFrame();

    expect(".o_pos_stock_badge").toHaveCount(0);
    expect.verifySteps([]);
});

test("refresh refetches every known product and the badge follows", async () => {
    let qty = 2;
    onRpc("product.product", "get_pos_stock_quantities", () => ({ 5: qty }));
    const store = await setupPosEnv();
    await mountCard(store.models["product.template"].get(5));
    await animationFrame();
    expect(".o_pos_stock_badge").toHaveText("2");

    qty = 0;
    getService("pos_stock").refresh();
    expect(".o_pos_stock_badge").toHaveText("2");
    await animationFrame();
    expect(".o_pos_stock_empty").toHaveText("0");
});

test("a validated order refetches the quantities the session already knows", async () => {
    let qty = 9;
    onRpc("product.product", "get_pos_stock_quantities", ({ args }) => {
        expect.step(`rpc ${args[0].join(",")}`);
        return { 5: qty };
    });
    const store = await setupPosEnv();
    await mountCard(store.models["product.template"].get(5));
    await animationFrame();
    expect.verifySteps(["rpc 5"]);

    const order = await getFilledOrder(store);
    store.checkPreparationStateAndSentOrderInPreparation = async () => {};
    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: order.uuid,
    });
    qty = 8;
    await validation.afterOrderValidation();
    await animationFrame();
    expect.verifySteps(["rpc 5"]);
    expect(".o_pos_stock_badge").toHaveText("8");
});

for (const key of ["Enter", " "]) {
    test(`keyboard ${key} activates once and prevents scrolling`, async () => {
        const store = await setupPosEnv();
        let clicks = 0;
        await mountCard(store.models["product.template"].get(5), {
            onClick: () => clicks++,
        });
        const card = getFixture().querySelector("article.product");
        const event = new KeyboardEvent("keydown", {
            key,
            bubbles: true,
            cancelable: true,
        });
        card.dispatchEvent(event);
        card.dispatchEvent(
            new KeyboardEvent("keydown", { key, repeat: true, bubbles: true }),
        );
        expect(clicks).toBe(1);
        expect(event.defaultPrevented).toBe(true);
        const input = document.createElement("input");
        card.append(input);
        const childEvent = new KeyboardEvent("keydown", {
            key,
            bubbles: true,
            cancelable: true,
        });
        input.dispatchEvent(childEvent);
        expect(clicks).toBe(1);
        expect(childEvent.defaultPrevented).toBe(false);
    });
}
