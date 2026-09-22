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
        price_include_override: "tax_included",
        tax_group_id: 9001,
    },
    {
        id: 9002,
        name: "25%",
        amount: 25,
        amount_type: "percent",
        price_include_override: "tax_included",
        tax_group_id: 9002,
    },
    {
        id: 9003,
        name: "5%",
        amount: 5,
        amount_type: "percent",
        price_include_override: "tax_included",
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
const sum = (lines, field) => round2(lines.reduce((acc, l) => acc + l[field], 0));

function getSplitOrders(store, originOrder) {
    return store.models["pos.order"].filter(
        (o) => o.split_payment_origin_uuid === originOrder.uuid
    );
}

function getSplitLines(store, order) {
    return order.lines.filter((l) => l.product_id.id === store.config.split_payment_product_id.id);
}

describe("SplitPayment", () => {
    let store;

    beforeEach(async () => {
        store = await setupAndMountPosApp({ set_tip_after_payment: false });
    });

    test("Client A pay 5 over 37, one split payment product per group", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);

        const originOrder = store.getOrder();

        await Utils.setGuestCount(3);
        const amountPerGuest = originOrder.amountPerGuest();

        await Utils.clickPayButton();
        await Utils.splitAndPay("Card", "5");

        const splitOrders = getSplitOrders(store, originOrder);
        expect(splitOrders.length).toBe(1);

        const floatingOrder = splitOrders[0];
        expect(floatingOrder.state).toBe("paid");
        expect(floatingOrder.floating_order_name).toBe("Split Payment");

        const floatingTaxIds = floatingOrder.lines.map((l) => l.tax_ids.map((t) => t.id)[0]).sort();
        expect(floatingTaxIds).toEqual([9001, 9002].sort());

        const floatingSplitLines = getSplitLines(store, floatingOrder);
        const originSplitLines = getSplitLines(store, originOrder);

        expect(originSplitLines.length).toBe(floatingSplitLines.length);
        expect(originSplitLines.length).toBe(2);

        for (let i = 0; i < originSplitLines.length; i++) {
            const originLine = originSplitLines[i];
            const floatingLine = floatingSplitLines[i];
            expect(originLine.priceIncl).toBe(-floatingLine.priceIncl);
            expect(originLine.tax_ids).toEqual(floatingLine.tax_ids);
            expect(originLine.getFullProductName()).toInclude("Split Payment");
            expect(floatingLine.getFullProductName()).toInclude("Split Payment");
        }

        expect(sum(floatingSplitLines, "priceIncl")).toBe(5);
        expect(floatingOrder.payment_ids.length).toBe(1);
        expect(floatingOrder.payment_ids[0].amount).toBe(5);

        expect(amountPerGuest).toBe(originOrder.amountPerGuest());
        expect(originOrder.priceIncl).toBe(32);
        expect(originOrder.state).toBe("draft");
        expect(originOrder.payment_ids.length).toBe(0);
    });

    test("The Split and Pay button appears only when the amount paid by the customer is less than the total order amount.", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);

        await Utils.clickPayButton();
        await Utils.clickPaymentMethod("Card");
        await animationFrame();
        expect(Utils.isSplitAndPayButtonShown()).toBe(false);
        await Utils.clickValidatePayment();

        const originOrder = store.getOrder();
        expect(getSplitOrders(store, originOrder).length).toBe(0);
        expect(getSplitLines(store, originOrder).length).toBe(0);
        expect(originOrder.priceIncl).toBe(37);
        expect(originOrder.payment_ids.length).toBe(1);
        expect(originOrder.payment_ids[0].amount).toBe(37);
        expect(originOrder.state).toBe("paid");

        await Utils.clickNextOrder();
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);

        await Utils.clickPayButton();
        await Utils.clickPaymentMethod("Card");

        if (Utils.isMobile()) {
            await Utils.clickPaymentline();
            await animationFrame();
        }
        await Utils.enterNumpadValue(37 - 5);
        if (Utils.isMobile()) {
            await press("Enter");
        }
        await waitFor(".o_split_and_pay_button");
        expect(Utils.isSplitAndPayButtonShown()).toBe(true);
    });

    test("Full flow: several split payments then the last client pays normally", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);

        const originOrder = store.getOrder();
        expect(originOrder.priceIncl).toBe(49);
        await Utils.setGuestCount(3);
        await Utils.clickPayButton();

        await Utils.splitAndPay("Card", "16");
        expect(getSplitOrders(store, originOrder).length).toBe(1);
        expect(getSplitLines(store, originOrder).length).toBe(2);
        expect(sum(getSplitLines(store, originOrder), "priceIncl")).toBe(-16);
        expect(originOrder.priceIncl).toBe(33);
        await Utils.clickNextOrder();

        await Utils.clickTable("1");
        await Utils.splitAndPay("Card", "16");
        const splitOrders2 = getSplitOrders(store, originOrder);
        expect(splitOrders2.length).toBe(2);
        expect(getSplitLines(store, originOrder).length).toBe(2);
        expect(sum(getSplitLines(store, originOrder), "priceIncl")).toBe(-32);
        await Utils.clickNextOrder();

        await Utils.clickTable("1");
        await Utils.clickPaymentMethod("Card");
        await Utils.clickValidatePayment();

        expect(originOrder.state).toBe("paid");

        const totalPaid =
            sum(originOrder.payment_ids, "amount") +
            splitOrders2.reduce((acc, o) => acc + sum(o.payment_ids, "amount"), 0);
        expect(round2(totalPaid)).toBe(49);
    });
});
