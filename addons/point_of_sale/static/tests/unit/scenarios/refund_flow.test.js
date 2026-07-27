import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp, createComboSetup } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("test_refund_line_keep_attributes: refund keeps variant attributes", async () => {
    await setupAndMountPosApp();
    await Utils.clickDisplayedProduct("Cake");
    await waitFor(".modal");
    await contains(".modal .btn-primary").click();
    await animationFrame();
    expect(
        Utils.hasOrderline({
            productName: "Cake",
            quantity: "1",
            attributeLine: "Chocolate",
            price: "3.00",
        })
    ).toBe(true);
    await Utils.ensurePane("left");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();
    await waitFor(".product-screen");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");
    await animationFrame();

    await contains('.ticket-screen .order-row:contains("001")').click();
    await animationFrame();

    await Utils.sendBufferKeys("1");

    if (Utils.isMobile()) {
        await Utils.clickTicketReviewButton();
        await Utils.clickTicketAction("Refund");
    } else {
        await contains('.ticket-screen .pads button:contains("Refund")').click();
        await animationFrame();
    }

    await waitFor(".payment-screen");
    if (Utils.isMobile()) {
        await contains(".payment-screen .back-button").click();
    } else {
        await contains(".payment-screen .back").click();
    }
    await animationFrame();
    expect(
        Utils.hasOrderline({
            productName: "Cake",
            quantity: "-1",
            attributeLine: "Chocolate",
            price: "3.00",
        })
    ).toBe(true);
});

test("test_combo_refund_different_qty: refund combo with different quantities", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    patchWithCleanup(store, {
        async syncAllOrders() {
            return;
        },
    });
    createComboSetup(store, {
        id: 7500,
        name: "Office Combo",
        price: 40,
        combos: [
            {
                name: "Desk Accessories",
                items: [{ name: "Combo Product 3", price: 16, extraPrice: 2 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
                sequence: 1,
            },
            {
                name: "Desks",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 2,
                qtyMax: 2,
                sequence: 2,
            },
            {
                name: "Chairs",
                items: [{ name: "Combo Product 6", price: 30 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
                sequence: 3,
            },
        ],
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await waitFor(".modal");

    await Utils.selectComboItem("Combo Product 3");
    await Utils.selectComboItem("Combo Product 4");
    await Utils.selectComboItem("Combo Product 4");
    await Utils.selectComboItem("Combo Product 6");

    await Utils.confirmCombo();

    expect(Utils.hasOrderline({ productName: "Office Combo" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 4", quantity: "2" })).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();
    await waitFor(".product-screen");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");

    await contains('.ticket-screen .order-row:contains("001")').click();
    await animationFrame();

    await Utils.sendBufferKeys("1");
    await animationFrame();

    await Utils.ensureTicketPane("right");
    const findRefundText = (productName) => {
        const lines = [...document.querySelectorAll(".ticket-screen .orderline")];
        const line = lines.find((el) => el.textContent.includes(productName));
        if (!line) {
            return null;
        }
        const refund = line.querySelector(".refund");
        return refund ? refund.textContent.trim() : null;
    };

    expect(findRefundText("Office Combo")).toInclude("1");
    expect(findRefundText("Combo Product 4")).toInclude("2");
    expect(findRefundText("Combo Product 3")).toInclude("1");
    expect(findRefundText("Combo Product 6")).toInclude("1");

    if (Utils.isMobile()) {
        await Utils.clickTicketReviewButton();
        await Utils.clickTicketAction("Refund");
    } else {
        await contains('.ticket-screen .pads button:contains("Refund")').click();
        await animationFrame();
    }

    await waitFor(".payment-screen");
});

test("RefundFewQuantities: refund with quantities less than 0.5", async () => {
    await setupAndMountPosApp({ use_pricelist: false });
    await animationFrame();
    await Utils.clickDisplayedProduct("TEST");
    await Utils.sendBufferKeys(".", "0", "2");
    expect(Utils.hasOrderline({ productName: "TEST", quantity: "0.02" })).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
    await Utils.clickNextOrder();
    await waitFor(".product-screen");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");

    await contains('.ticket-screen .order-row:contains("001")').click();
    await animationFrame();

    await Utils.sendBufferKeys("0", ".", "0", "2");
    await animationFrame();

    await Utils.ensureTicketPane("right");
    const refundEl = document.querySelector(".ticket-screen .refund");
    expect(refundEl).not.toBe(null);
    expect(refundEl.textContent).toInclude("0.02");

    if (Utils.isMobile()) {
        await Utils.clickTicketReviewButton();
        await Utils.clickTicketAction("Refund");
    } else {
        await contains('.ticket-screen .pads button:contains("Refund")').click();
        await animationFrame();
    }
    await waitFor(".payment-screen");
    if (Utils.isMobile()) {
        await contains(".payment-screen .back-button").click();
    } else {
        await contains(".payment-screen .back").click();
    }
    await animationFrame();
    expect(Utils.hasOrderline({ productName: "TEST", quantity: "-0.02" })).toBe(true);
});
