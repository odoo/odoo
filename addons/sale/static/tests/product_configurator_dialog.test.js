import { expect, test } from "@odoo/hoot";
import { click, press, queryFirst, queryText } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { ProductProduct } from "@sale/js/models/product_product";
import { ProductCard } from "@sale/js/product_card/product_card";
import { ProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";
import {
    defineModels,
    getService,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/ui/main_components_container";

import { saleModels } from "./sale_test_helpers.js";

defineModels(saleModels);

function productPayload(price) {
    return {
        product_tmpl_id: 3,
        id: 7,
        display_name: "Chair",
        description_sale: false,
        price,
        quantity: 1,
        uom: { id: 1, display_name: "Units" },
        attribute_lines: [],
        archived_combinations: [],
        exclusions: {},
        parent_exclusions: {},
        show_extra_price: true,
    };
}

async function openConfigurator() {
    await mountWithCleanup(MainComponentsContainer);
    getService("dialog").add(ProductConfiguratorDialog, {
        productTemplateId: 3,
        ptavIds: [],
        customPtavs: [],
        quantity: 1,
        currencyId: 1,
        soDate: "2026-01-01 00:00:00",
        save: () => {},
        discard: () => {},
    });
    await animationFrame();
    await animationFrame();
}

const price = () =>
    queryText("[name='sale_product_configurator_formatted_price']").trim();
const total = () => queryText("[name='sale_product_configurator_list_total']").trim();
const quantity = () => queryFirst("[name='sale_quantity']").value;

test("quantity: a superseded price response does not overwrite the current one", async () => {
    const pending = [];
    onRpc("/sale/product_configurator/get_values", () => ({
        products: [productPayload(10)],
        optional_products: [],
        currency_id: 1,
    }));
    onRpc("/sale/product_configurator/update_combination", () => {
        const deferred = new Deferred();
        pending.push(deferred);
        return deferred;
    });

    await openConfigurator();
    expect(price()).toInclude("10");

    const plus = queryFirst("[name='sale_quantity_button_plus']");
    click(plus);
    await animationFrame();
    click(plus);
    await animationFrame();
    expect(pending).toHaveLength(2);

    pending[1].resolve({ price: "30", show_extra_price: true });
    pending[0].resolve({ price: "20", show_extra_price: true });
    await animationFrame();
    await animationFrame();

    expect(quantity()).toBe("3");
    expect(price()).toInclude("30");
    expect(total()).toInclude("90");
});

test("quantity: the newest response still applies when it arrives last", async () => {
    const pending = [];
    onRpc("/sale/product_configurator/get_values", () => ({
        products: [productPayload(10)],
        optional_products: [],
        currency_id: 1,
    }));
    onRpc("/sale/product_configurator/update_combination", () => {
        const deferred = new Deferred();
        pending.push(deferred);
        return deferred;
    });

    await openConfigurator();
    const plus = queryFirst("[name='sale_quantity_button_plus']");
    click(plus);
    await animationFrame();
    click(plus);
    await animationFrame();

    pending[0].resolve({ price: "20", show_extra_price: true });
    pending[1].resolve({ price: "30", show_extra_price: true });
    await animationFrame();
    await animationFrame();

    expect(quantity()).toBe("3");
    expect(price()).toInclude("30");
    expect(total()).toInclude("90");
});

test("ProductCard is operable from the keyboard", async () => {
    const clicks = [];
    class Parent extends Component {
        static components = { ProductCard };
        static template = xml`<ProductCard product="product" onClick="() => this.onClick()"/>`;
        static props = {};
        setup() {
            this.product = new ProductProduct({
                id: 1,
                product_tmpl_id: 1,
                display_name: "Card",
                image_src: "",
                description: "",
                ptals: [],
            });
        }
        onClick() {
            clicks.push("activated");
        }
    }
    await mountWithCleanup(Parent, { componentEnv: { currency: { id: 1 } } });

    const card = queryFirst("article.product-card");
    expect(card).toHaveAttribute("role", "button");
    card.focus();

    await press("Enter");
    expect(clicks).toHaveLength(1);

    await press(" ");
    expect(clicks).toHaveLength(2);

    const spaceEvent = new KeyboardEvent("keydown", {
        key: " ",
        bubbles: true,
        cancelable: true,
    });
    card.dispatchEvent(spaceEvent);
    expect(spaceEvent.defaultPrevented).toBe(true);
});
