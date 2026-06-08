import { test, expect } from "@odoo/hoot";
import { animationFrame, waitFor, waitUntil } from "@odoo/hoot-dom";
import { click } from "@mail/../tests/mail_test_helpers";
import { mountWithCleanup, contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { Chrome } from "@point_of_sale/app/pos_app";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "../data/generate_model_definitions";
import { scanBarcode, setupPosEnv } from "../utils";

definePosModels();

async function mountChromeOnProductScreen(store, order = store.getOrder() || store.addNewOrder()) {
    store.session.state = "opened";
    store.setOrder(order);
    store.navigate("ProductScreen", { orderUuid: order.uuid });

    await mountWithCleanup(Chrome, {
        props: { disableLoader: () => {} },
    });
    await waitFor(".product-screen");
    return order;
}

test.tags("desktop");
test("test_click_all_orders_keep_customer: all orders keeps the selected customer", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].create({
        id: 9101,
        name: "Partner Test 1",
        street: "1 Infinite Loop",
        city: "Cupertino",
        zip: "95014",
        address: "1 Infinite Loop Cupertino",
        barcode: false,
        email: false,
        phone: false,
        lang: "en_US",
        parent_name: false,
        fiscal_position_id: false,
        invoice_emails: "",
        property_product_pricelist: false,
        write_date: "2025-07-03 12:38:12",
    });

    await mountChromeOnProductScreen(store);

    await contains(".set-partner").click();
    await waitFor(".partner-list");
    await contains(`.partner-line[data-id="${partner.id}"]`).click();

    expect(store.getOrder().partner_id.id).toBe(partner.id);

    await contains(".set-partner").click();
    await waitFor(".partner-list");
    await contains(`.partner-line[data-id="${partner.id}"] .fa-bars`).click();
    await waitFor(".dropdown-item");
    await click(".dropdown-item", { text: "All Orders" });
    await waitFor(".ticket-screen");

    await contains(".register-label").click();
    await waitFor(".product-screen");

    expect(store.getOrder().partner_id.id).toBe(partner.id);
    expect(document.querySelector(".set-partner").textContent.includes("Partner Test 1")).toBe(
        true
    );
});

test("test_ctrl_number_ignored: ctrl+number does not change the order line", async () => {
    const store = await setupPosEnv();
    store.session.state = "opened";
    const order = store.addNewOrder();

    await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });

    await contains('.product-sortable[data-product-id="5"]').click();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].qty).toBe(1);

    window.dispatchEvent(new KeyboardEvent("keyup", { key: "5", ctrlKey: true }));
    await new Promise((resolve) => setTimeout(resolve, 350));

    expect(order.lines[0].qty).toBe(1);
    expect(order.lines[0].displayPrice).toBe(3.45);
});

test("test_quantity_package_of_non_basic_unit: barcode packaging sets the packaged quantity", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupPosEnv();
    store.session.state = "opened";
    const order = store.addNewOrder();
    const baseUom = store.models["uom.uom"].create({
        id: 9301,
        name: "test unit uom",
        factor: 1,
        is_pos_groupable: false,
        parent_path: "9301/",
    });
    const packageUom = store.models["uom.uom"].create({
        id: 9302,
        name: "Pack of 12 unit",
        factor: 12,
        is_pos_groupable: true,
        parent_path: "9301/9302/",
    });
    const category = store.models["pos.category"].get(1);
    const product = store.models["product.template"].create({
        id: 9303,
        name: "Cord",
        display_name: "Cord",
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: baseUom,
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [],
        attribute_line_ids: [],
        combo_ids: [],
        pos_categ_ids: [category],
    });
    const variant = store.models["product.product"].create({
        id: 9304,
        name: "Cord",
        display_name: "Cord",
        product_tmpl_id: product,
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: [category.id],
    });
    product.product_variant_ids = [variant];
    store.models["product.uom"].create({
        id: 9305,
        barcode: "555555",
        product_id: variant,
        uom_id: packageUom,
    });

    await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });

    await scanBarcode(store, "555555");

    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].product_id.id).toBe(variant.id);
    expect(order.lines[0].qty).toBe(12);
});

test.tags("desktop");
test("test_preset_customer_selection: selecting a customer preserves the preset address flow", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].create({
        id: 9201,
        name: "Partner Full",
        street: "77 Santa Barbara Rd",
        city: "Pleasant Hill",
        zip: "94523",
        address: "77 Santa Barbara Rd Pleasant Hill",
        barcode: false,
        email: false,
        phone: false,
        lang: "en_US",
        parent_name: false,
        fiscal_position_id: false,
        invoice_emails: "",
        property_product_pricelist: false,
        write_date: "2025-07-03 12:38:12",
    });
    const preset = store.models["pos.preset"].get(4);
    store.config.use_presets = true;
    store.config.default_preset_id = preset;
    store.config.available_preset_ids = [preset];
    const order = store.addNewOrder();
    order.setPreset(preset);

    await mountChromeOnProductScreen(store, order);

    await contains(".set-partner").click();
    await waitFor(".partner-list");
    await contains(".modal input").edit("Partner Full", { confirm: false });
    await contains(`.partner-line[data-id="${partner.id}"]`).click();

    expect(order.partner_id.id).toBe(partner.id);
    expect(document.querySelector(".set-partner").textContent.includes("Partner Full")).toBe(true);

    await contains(".orders-button").click();
    await waitFor(".ticket-screen");

    expect(
        document
            .querySelector(".address-cell")
            .textContent.includes("77 Santa Barbara Rd Pleasant Hill")
    ).toBe(true);
});

test.tags("desktop");
test("test_pos_large_amount_confirmation_dialog: validating a very large payment asks for confirmation", async () => {
    const store = await setupPosEnv();
    store.session.state = "opened";
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);

    await mountChromeOnProductScreen(store, order);

    await contains(".pay-order-button").click();
    await waitFor(".payment-screen");

    await click(".paymentmethod", { text: "Cash" });
    order.payment_ids[0].setAmount(5000);
    await animationFrame();

    await contains(".validation-button.next").click();
    await waitUntil(() =>
        document.querySelector(".modal-title")?.textContent.includes("Please Confirm Large Amount")
    );

    await click(".modal .btn-primary");
    await waitUntil(() => order.state === "paid");

    expect(order.state).toBe("paid");
});
