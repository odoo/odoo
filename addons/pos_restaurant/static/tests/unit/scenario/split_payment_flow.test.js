import { describe, expect, test, beforeEach } from "@odoo/hoot";
import { animationFrame, waitFor, press } from "@odoo/hoot-dom";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as ResUiUtils from "@pos_restaurant/../tests/unit/ui_utils";

import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";
import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";
import { AccountTaxGroup } from "@point_of_sale/../tests/unit/data/account_tax_group.data";
import { AccountTax } from "@point_of_sale/../tests/unit/data/account_tax.data";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

const Utils = { ...PosUiUtils, ...ResUiUtils };
const productA20 = "Product A (20%)";
const productB25 = "Product B (25%)";
const productC25_5 = "Product C (25% + 5%)";

AccountTaxGroup._records.push(
    { id: 9001, name: "TAX 20%", pos_receipt_label: "Tax" },
    { id: 9002, name: "TAX 25%", pos_receipt_label: "Tax" },
    { id: 9003, name: "TAX 5%", pos_receipt_label: "Tax" }
);

AccountTax._records.push(
    {
        id: 9001,
        name: "20%",
        amount: 20,
        amount_type: "percent",
        price_include: false,
        tax_group_id: 9001,
    },
    {
        id: 9002,
        name: "25%",
        amount: 25,
        amount_type: "percent",
        price_include: false,
        tax_group_id: 9002,
    },
    {
        id: 9003,
        name: "5%",
        amount: 5,
        amount_type: "percent",
        price_include: false,
        tax_group_id: 9003,
    }
);

function addProduct({ id, name, price, taxes, type = "consu" }) {
    ProductTemplate._records.push({
        id,
        name,
        display_name: name,
        type,
        list_price: price,
        taxes_id: taxes,
        product_variant_ids: [],
        available_in_pos: true,
    });
    ProductProduct._records.push({
        id,
        product_tmpl_id: id,
        name,
        display_name: name,
        type,
        lst_price: price,
        taxes_id: taxes,
        available_in_pos: true,
    });
}

addProduct({ id: 9001, name: productA20, price: 10, taxes: [9001] });
addProduct({ id: 9002, name: productB25, price: 20, taxes: [9002] });
addProduct({ id: 9003, name: "Split Payment Product", price: 0, taxes: [], type: "service" });
addProduct({ id: 9004, name: productC25_5, price: 15, taxes: [9002, 9003] });

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    split_payment_product_id: 9003,
}));

definePosModels();

const round2 = (n) => Math.round(n * 100) / 100;

function getSplitOrders(store, originOrder) {
    return store.models["pos.order"].filter(
        (order) => order.split_origin_order_id?.uuid === originOrder.uuid
    );
}

function splitLinesSummary(order) {
    return order.splitPaymentLines
        .map((line) => ({
            taxIds: line.tax_ids.map((tax) => tax.id).sort(),
            priceIncl: round2(line.priceIncl),
            priceExcl: round2(line.priceExcl),
        }))
        .sort((a, b) => a.taxIds.join().localeCompare(b.taxIds.join()));
}

function receiptTaxBreakdown(order) {
    const taxGroups = order.prices.taxDetails.subtotals[0]?.tax_groups || [];
    return Object.fromEntries(
        taxGroups.map((group) => [
            group.id,
            { base: round2(group.base_amount_currency), tax: round2(group.tax_amount_currency) },
        ])
    );
}

function expectTaxBreakdownPreserved(originOrder, splitOrders, initialBreakdown) {
    const total = {};
    for (const order of [originOrder, ...splitOrders]) {
        for (const [groupId, { base, tax }] of Object.entries(receiptTaxBreakdown(order))) {
            total[groupId] ??= { base: 0, tax: 0 };
            total[groupId].base = round2(total[groupId].base + base);
            total[groupId].tax = round2(total[groupId].tax + tax);
        }
    }
    expect(total).toEqual(initialBreakdown);
}

async function enterPaymentAmount(amount) {
    if (Utils.isMobile()) {
        await Utils.clickPaymentline();
        await animationFrame();
    }
    await Utils.enterNumpadValue(amount);
    if (Utils.isMobile()) {
        await press("Enter");
    }
    await animationFrame();
}

describe("SplitPayment", () => {
    let store;

    beforeEach(async () => {
        store = await setupAndMountPosApp({ set_tip_after_payment: false });
    });

    test("Split and Pay button: enabled only for a validated partial payment, disabled when a customer is required", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);
        const order = store.getOrder();
        const partner = store.models["res.partner"].get(3);
        const customerAccount = store.models["pos.payment.method"].get(3);
        const splitButton = ".o_split_and_pay_button";

        await Utils.clickPayButton();
        await Utils.clickPaymentMethod("Card");
        await animationFrame();
        expect(Utils.isSplitAndPayButtonShown()).toBe(false);

        await enterPaymentAmount("10");
        await waitFor(splitButton);
        expect(splitButton).toBeEnabled();

        const cardLine = order.payment_ids[0];
        cardLine.setPaymentStatus("waiting");
        await animationFrame();
        expect(splitButton).not.toBeEnabled();
        cardLine.setPaymentStatus("done");
        await animationFrame();
        expect(splitButton).toBeEnabled();

        const pendingLine = order.addPaymentline(cardLine.payment_method_id).data;
        pendingLine.setAmount(1);
        pendingLine.setPaymentStatus("pending");
        await animationFrame();
        expect(splitButton).not.toBeEnabled();
        order.removePaymentline(pendingLine);
        await animationFrame();
        expect(splitButton).toBeEnabled();

        order.setToInvoice(true);
        await animationFrame();
        expect(splitButton).not.toBeEnabled();
        order.setPartner(partner);
        await animationFrame();
        expect(splitButton).toBeEnabled();

        order.setPartner(false);
        order.setToInvoice(false);
        await animationFrame();
        expect(splitButton).toBeEnabled();

        order.addPaymentline(customerAccount).data.setAmount(1);
        await animationFrame();
        expect(splitButton).not.toBeEnabled();
        order.setPartner(partner);
        await animationFrame();
        expect(splitButton).toBeEnabled();
    });

    test("Basic example: a guest pays 10% (3.70) of a 37.00 order with 20% and 25% taxes", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);

        // A = 10.00 + 2.00 (20%), B = 20.00 + 5.00 (25%).
        const originOrder = store.getOrder();
        expect(originOrder.priceIncl).toBe(37);
        expect(receiptTaxBreakdown(originOrder)).toEqual({
            9001: { base: 10, tax: 2 },
            9002: { base: 20, tax: 5 },
        });

        await Utils.clickPayButton();
        await Utils.splitAndPay("Card", "3.70");

        const splitOrders = getSplitOrders(store, originOrder);
        expect(splitOrders.length).toBe(1);
        const [floatingOrder] = splitOrders;
        expect(floatingOrder.state).toBe("paid");
        expect(floatingOrder.payment_ids.map((p) => p.amount)).toEqual([3.7]);
        expect(splitLinesSummary(floatingOrder)).toEqual([
            { taxIds: [9001], priceIncl: 1.2, priceExcl: 1 },
            { taxIds: [9002], priceIncl: 2.5, priceExcl: 2 },
        ]);
        expect(receiptTaxBreakdown(floatingOrder)).toEqual({
            9001: { base: 1, tax: 0.2 },
            9002: { base: 2, tax: 0.5 },
        });

        expect(originOrder.state).toBe("draft");
        expect(originOrder.payment_ids.length).toBe(0);
        expect(originOrder.priceIncl).toBe(33.3);
        expect(splitLinesSummary(originOrder)).toEqual([
            { taxIds: [9001], priceIncl: -1.2, priceExcl: -1 },
            { taxIds: [9002], priceIncl: -2.5, priceExcl: -2 },
        ]);
        expect(receiptTaxBreakdown(originOrder)).toEqual({
            9001: { base: 9, tax: 1.8 },
            9002: { base: 18, tax: 4.5 },
        });
    });

    test("Prorata rounding: paying 1.00 of 37.00 loses no cent", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);
        const originOrder = store.getOrder();
        const initialBreakdown = receiptTaxBreakdown(originOrder);

        await Utils.clickPayButton();
        await Utils.splitAndPay("Card", "1");

        const [floatingOrder] = getSplitOrders(store, originOrder);
        expect(floatingOrder.priceIncl).toBe(1);
        expect(splitLinesSummary(floatingOrder).map((l) => l.priceIncl)).toEqual([0.32, 0.68]);
        expect(originOrder.priceIncl).toBe(36);
        expectTaxBreakdownPreserved(originOrder, [floatingOrder], initialBreakdown);
    });

    test("Lines with several taxes keep their tax combination on the split lines", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productC25_5);
        const originOrder = store.getOrder();
        expect(originOrder.priceIncl).toBe(31.5);
        const initialBreakdown = receiptTaxBreakdown(originOrder);

        await Utils.clickPayButton();
        await Utils.splitAndPay("Card", "6.30");

        const [floatingOrder] = getSplitOrders(store, originOrder);
        expect(splitLinesSummary(floatingOrder)).toEqual([
            { taxIds: [9001], priceIncl: 2.4, priceExcl: 2 },
            { taxIds: [9002, 9003], priceIncl: 3.9, priceExcl: 3 },
        ]);
        expect(receiptTaxBreakdown(floatingOrder)).toEqual({
            9001: { base: 2, tax: 0.4 },
            9002: { base: 3, tax: 0.75 },
            9003: { base: 3, tax: 0.15 },
        });
        expectTaxBreakdownPreserved(originOrder, [floatingOrder], initialBreakdown);
    });

    test("4 guests: 3 guests pay their share through Split and Pay, the 4th pays the rest", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);
        const originOrder = store.getOrder();
        const initialBreakdown = receiptTaxBreakdown(originOrder);
        await Utils.setGuestCount(4);

        await Utils.clickPayButton();
        for (let guest = 1; guest <= 3; guest++) {
            if (guest > 1) {
                await Utils.clickTable("1");
            }
            expect(originOrder.amountPerGuest()).toBe(9.25);
            await waitFor(".paymentlines-container .message:contains('9.25')");
            await Utils.splitAndPay("Card", "9.25");

            const splitOrders = getSplitOrders(store, originOrder);
            expect(splitOrders.length).toBe(guest);
            expect(splitOrders.every((order) => order.state === "paid")).toBe(true);
            expect(splitLinesSummary(originOrder)).toEqual([
                { taxIds: [9001], priceIncl: -3 * guest, priceExcl: -2.5 * guest },
                { taxIds: [9002], priceIncl: -6.25 * guest, priceExcl: -5 * guest },
            ]);
            expect(originOrder.amountAlreadySplitPaid).toBe(9.25 * guest);
            expectTaxBreakdownPreserved(originOrder, splitOrders, initialBreakdown);
            await Utils.clickNextOrder();
        }

        await Utils.clickTable("1");
        await Utils.clickPaymentMethod("Card");
        await Utils.clickValidatePayment();
        expect(originOrder.state).toBe("paid");
        expect(originOrder.payment_ids.map((p) => p.amount)).toEqual([9.25]);
    });

    test("Merged tables stay merged after a split payment", async () => {
        const table1 = store.models["restaurant.table"].get(2);
        const table3 = store.models["restaurant.table"].get(3);
        table3.parent_id = table1;

        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);
        const originOrder = store.getOrder();

        await Utils.clickPayButton();
        await Utils.splitAndPay("Card", "3.70");
        const [floatingOrder] = getSplitOrders(store, originOrder);
        expect(floatingOrder.table_id.id).toBe(table1.id);
        expect(table3.parent_id?.id).toBe(table1.id);
        await Utils.clickNextOrder();

        await Utils.clickTable("1");
        await Utils.clickPaymentMethod("Card");
        await Utils.clickValidatePayment();
        expect(table3.parent_id).toBe(undefined);
    });
});
