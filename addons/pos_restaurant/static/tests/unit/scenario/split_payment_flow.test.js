import { describe, expect, test, beforeEach } from "@odoo/hoot";
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

AccountTaxGroup._records.push({
    id: 9001,
    name: "TAX 20%",
    pos_receipt_label: "Tax",
});

AccountTaxGroup._records.push({
    id: 9002,
    name: "TAX 25%",
    pos_receipt_label: "Tax",
});

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
    }
);

ProductTemplate._records.push({
    id: 9001,
    name: productA20,
    display_name: productA20,
    type: "consu",
    list_price: 10,
    taxes_id: [9001],
    product_variant_ids: [],
    available_in_pos: true,
});

ProductProduct._records.push({
    id: 9001,
    product_tmpl_id: 9001,
    name: productA20,
    display_name: productA20,
    type: "consu",
    lst_price: 10,
    taxes_id: [9001],
    available_in_pos: true,
});

ProductTemplate._records.push({
    id: 9002,
    name: productB25,
    display_name: productB25,
    type: "consu",
    list_price: 20,
    taxes_id: [9002],
    product_variant_ids: [],
    available_in_pos: true,
});

ProductProduct._records.push({
    id: 9002,
    product_tmpl_id: 9002,
    name: productB25,
    display_name: productB25,
    type: "consu",
    lst_price: 20,
    taxes_id: [9002],
    available_in_pos: true,
});

ProductTemplate._records.push({
    id: 9003,
    name: "Split Payment Product",
    display_name: "Split Payment",
    type: "service",
    list_price: 0,
    taxes_id: [],
    product_variant_ids: [],
    available_in_pos: true,
});

ProductProduct._records.push({
    id: 9003,
    product_tmpl_id: 9003,
    name: "Split Payment Product",
    display_name: "Split Payment",
    type: "service",
    list_price: 0,
    taxes_id: [],
    available_in_pos: true,
});

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    split_payment_product_id: 9003,
}));

definePosModels();

describe("SplitPayment", () => {
    let store;

    beforeEach(async () => {
        store = await setupAndMountPosApp({ set_tip_after_payment: false });
    });

    test("Client A pay 5 over 10, one split payment product per group", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);

        const originOrder = store.getOrder();

        await Utils.clickPayButton();
        await Utils.splitAndPay("Card", "5");

        const splitOrders = store.models["pos.order"].filter(
            (o) => o.split_payment_origin_uuid === originOrder.uuid
        );
        expect(splitOrders.length).toBe(1);

        const floatingOrder = splitOrders[0];
        expect(floatingOrder.state).toBe("paid");

        const floatingTaxIds = floatingOrder.lines.map((l) => l.tax_ids.map((t) => t.id)[0]).sort();
        expect(floatingTaxIds).toEqual([9001, 9002].sort());

        const originSplitLines = originOrder.lines.filter(
            (l) => l.product_id.id === store.config.split_payment_product_id.id
        );
        expect(originSplitLines.length).toBe(2);
        expect(originOrder.priceIncl).toBe(32);
        expect(originOrder.state).toBe("draft");
    });
});
