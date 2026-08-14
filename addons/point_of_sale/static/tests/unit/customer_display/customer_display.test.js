import { test, expect, queryOne, waitFor } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { isVisible } from "@html_editor/utils/dom_info";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";
import { mountPosDialog, setupPosEnv } from "../utils";
import { setupCustomerDisplay, CustomerDisplayAssertions as Assert } from "./utils";
import { QrCodeCustomerDisplay } from "@point_of_sale/app/customer_display/customer_display_qr_code_popup";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { ScaleInterface } from "@point_of_sale/app/utils/scale/scale_interface";

definePosModels();

test.tags("desktop");
test("customer display QR popup shows QR dialog from UI button", async () => {
    const store = await setupPosEnv();
    await mountPosDialog(QrCodeCustomerDisplay, {
        customerDisplayURL: `${store.config._base_url}/pos_customer_display/${store.config.id}/test-device`,
    });

    await contains("button:contains('Display QR')").click();
    await waitFor("#CustomerDisplayqrCode");

    const qrImage = queryOne("#CustomerDisplayqrCode");
    expect(qrImage.getAttribute("src").includes("data:image")).toBe(true);
});

test("customer display renders selected line, notes and total", async () => {
    const [store] = await setupCustomerDisplay();
    await store.addLineToCurrentOrder({
        product_tmpl_id: 5,
        customer_note: "No onions",
        note: '[{"text":"VIP","colorIndex":2}]',
    });

    await Assert.hasOrderLine({ productName: "TEST", price: "3.45", withClass: ".selected" });
    await Assert.hasOrderlineCount(1);

    expect(".customer-note").toHaveText("No onions");
    expect(".internal-note-container").toHaveText("VIP");
    Assert.hasTotal({ total: "3.45", subtotal: "3.00", taxes: "0.45" });
});

test("customer display screen saver", async () => {
    mockDate("2021-02-10 00:00:00");
    const [store] = await setupCustomerDisplay();
    store.navigate("SaverScreen");
    await Assert.checkScreenSaver();
    expect(queryOne(".timer-date-container")).toHaveText("Wednesday\nFebruary, 10, 2021");
});

test("CustomerDisplayTour: full customer display flow with products and payments", async () => {
    const [store, order, display] = await setupCustomerDisplay();
    // Line1 - unselected line
    await store.addLineToCurrentOrder({ product_tmpl_id: 5 });
    order.deselectOrderline();
    await Assert.hasOrderLine({ productName: "TEST", price: "3.45", withoutClass: ".selected" });
    await Assert.hasOrderlineCount(1);
    expect(display.data().selectedLineUuid).toBeEmpty();
    // Line2 - selected line
    await store.addLineToCurrentOrder({ product_tmpl_id: 6 });
    await Assert.hasOrderLine({ productName: "TEST 2", price: "3.75", withClass: ".selected" });
    await Assert.hasOrderlineCount(2);
    expect(display.data().selectedLineUuid).toBe(order.lines[1].uuid);
    // add payment Line
    const cashPm = store.models["pos.payment.method"].get(1);
    order.addPaymentline(cashPm);
    await Assert.hasPaymentLine("Cash", "7.20");
    // Pay Order
    await store.validateOrder();
    await Assert.checkThankyou();
    // New Order
    const order2 = store.addNewOrder();
    store.setOrder(order2);
    await Assert.checkWelcome();
    await Assert.hasOrderlineCount(0);
    // Navigate to screen saver
    store.navigate("SaverScreen");
    await Assert.checkScreenSaver();
});

test("CustomerDisplayTourScroll: customer display scrolls to selected orderline", async () => {
    patchWithCleanup(PosOrderline.prototype, {
        // Ovveride so that we could add multiple line for the same products in the order.
        canBeMergedWith(orderline) {
            return false;
        },
    });
    const [store] = await setupCustomerDisplay();
    for (let i = 0; i < 20; i++) {
        await store.addLineToCurrentOrder({ product_tmpl_id: 5 });
    }
    await Assert.hasOrderlineCount(20);

    const orderContainer = queryOne(".order-container");
    const orderLine = queryOne(".orderline:last-child");

    const waitForScroll = (el) =>
        new Promise((resolve) => {
            const check = () => (el.scrollTop > 0 ? resolve() : requestAnimationFrame(check));
            check();
        });

    await waitForScroll(orderContainer);

    expect(orderContainer.scrollTop).toBeGreaterThan(0);
    expect(isVisible(orderLine)).toBe(true);
});

test("CustomerDisplayTourWithQr: customer display shows QR code for payment", async () => {
    patchWithCleanup(PosStore.prototype, {
        async weighProduct() {
            this.scale.weight = 7.21;
            return 7.21;
        },
    });
    const [store] = await setupCustomerDisplay();
    const scale = new ScaleInterface(store);
    store.scale = scale;
    await store.initCustomerDisplay();

    const product = store.models["product.template"].get(5);
    product.to_weight = true;
    await store.addLineToCurrentOrder({ product_tmpl_id: product });
    // UI Check
    await Assert.hasOrderLine({ productName: "TEST", price: "24.87", quantity: "7.21" });
    expect(".o_customer_display_scale").toHaveCount(1);
    expect(".o_customer_display_scale h4").toHaveText("Weighing Product:TEST");
    expect(".o_customer_display_scale:contains('Gross Weight: 7.21 Units)").toHaveCount(1);
    expect(".o_customer_display_scale .product-price").toHaveText("$ 3.45 / Units");
    expect(".o_customer_display_scale .computed-price").toHaveText("$ 24.87");
});
