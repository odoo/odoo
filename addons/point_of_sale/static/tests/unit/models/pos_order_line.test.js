import { test, expect, describe } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

function getAllPricesData(otherData = {}) {
    return {
        "pos.order": [
            {
                id: 1,
                name: "Test Order",
                lines: [1],
            },
            {
                id: 2,
                name: "Test Combo order",
            },
        ],
        "pos.order.line": [
            {
                id: 1,
                order_id: 1,
                product_id: 5,
                price_unit: 100.0,
                qty: 2,
                tax_ids: [1],
            },
            {
                id: 2,
                order_id: 2,
                product_id: 7,
                price_unit: 0.0,
                qty: 1,
                combo_line_ids: [3, 4],
                tax_ids: [],
            },
            {
                id: 3,
                order_id: 2,
                product_id: 8,
                price_unit: 1,
                qty: 2,
                combo_parent_id: 2,
                tax_ids: [],
            },
            {
                id: 4,
                order_id: 2,
                product_id: 10,
                price_unit: 8,
                qty: 1,
                combo_parent_id: 2,
                tax_ids: [],
            },
        ],
        ...otherData,
    };
}

test("[get prices()] Base test", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const data = models.loadConnectedData(getAllPricesData());

    const lineTax = data["pos.order.line"][0].prices;
    expect(lineTax.total_included).toBe(230.0);
    expect(lineTax.total_excluded).toBe(200.0);
    expect(lineTax.taxes_data[0].base_amount).toBe(200.0);
    expect(lineTax.taxes_data[0].tax_amount).toBe(30.0);

    // Test with line qty = 0
    data["pos.order.line"][0].qty = 0;
    const zeroQtyLineTax = data["pos.order.line"][0].prices;
    expect(zeroQtyLineTax.total_included).toBe(0.0);
    expect(zeroQtyLineTax.total_excluded).toBe(0.0);
    expect(zeroQtyLineTax.taxes_data[0].base_amount).toBe(0.0);
    expect(zeroQtyLineTax.taxes_data[0].tax_amount).toBe(0.0);
});

test("[get prices()] with discount applied", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const data = models.loadConnectedData(getAllPricesData());
    const orderLine = data["pos.order.line"][0];

    // Prices with a discount of 10% applied: 230 * 0.9 = 207.0
    orderLine.setDiscount(10.0); // 10% discount
    const lineTax = orderLine.prices;
    expect(lineTax.total_included).toBe(207.0);
    expect(lineTax.total_excluded).toBe(180.0);
    expect(lineTax.taxes_data[0].tax_amount).toBe(27.0);

    // Price with a discount of 100% applied
    orderLine.setDiscount(100.0);
    const updatedLineTax = orderLine.prices;
    expect(updatedLineTax.total_excluded).toBe(0.0);
    expect(updatedLineTax.total_included).toBe(0.0);
    expect(updatedLineTax.taxes_data[0].tax_amount).toBe(0.0);
});

test("[get prices()] with multiple taxes settings", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const rawData = getAllPricesData();
    const product = models["product.product"].get(5);
    product.taxes_id = models["account.tax"].readMany([1, 2]); // Set two taxes on the product
    rawData["pos.order.line"][0].qty = 1;
    rawData["pos.order.line"][0].tax_ids = [1, 2];

    const data = models.loadConnectedData(rawData);
    const orderLine = data["pos.order.line"][0];

    // Test with two taxes applied (15% and 25%)
    const lineTax = orderLine.prices;
    expect(lineTax.total_excluded).toBe(100.0);
    expect(lineTax.total_included).toBe(140.0);
    expect(lineTax.taxes_data[0].tax_amount).toBe(15.0);
    expect(lineTax.taxes_data[1].tax_amount).toBe(25.0);

    // Test with "include_base_amount" and "include_base_amount" to true for both taxes
    models["account.tax"].get(1).include_base_amount = true;
    models["account.tax"].get(2).include_base_amount = true;
    orderLine.order_id.triggerRecomputeAllPrices(); // Force the recompute because updating taxes do not trigger it
    const updatedLineTax = orderLine.prices;
    expect(updatedLineTax.total_excluded).toBe(100.0);
    expect(updatedLineTax.total_included).toBe(143.75);
    expect(updatedLineTax.taxes_data[0].tax_amount).toBe(15.0);
    expect(updatedLineTax.taxes_data[1].tax_amount).toBe(28.75);

    // Test without any taxes
    product.taxes_id = [];
    orderLine.tax_ids = []; // Do not need to force the recompute here, changing line taxes does it for us
    const noTaxLine = data["pos.order.line"][0].prices;
    expect(noTaxLine.total_excluded).toBe(100.0);
    expect(noTaxLine.total_included).toBe(100.0);
    expect(noTaxLine.taxes_data).toHaveLength(0);
});

test("[get prices()] with fixed-amount tax", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const data = models.loadConnectedData(getAllPricesData());
    models["account.tax"].get(1).amount_type = "fixed";
    const orderLine = data["pos.order.line"][0];
    orderLine.qty = 3;
    orderLine.price_unit = 10.0;
    const lineTax = orderLine.prices;
    // 3 * 10 = 30, tax = 3 * 15 = 45
    expect(lineTax.total_excluded).toBe(30.0);
    expect(lineTax.total_included).toBe(75.0);
    expect(lineTax.taxes_data[0].tax_amount).toBe(45.0);
});

test("[get prices()] with one price-included and one price-excluded tax", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const product = models["product.product"].get(5);
    const rawData = getAllPricesData();
    models["account.tax"].get(1).price_include = true;
    product.taxes_id = models["account.tax"].readMany([1, 2]);
    rawData["pos.order.line"][0].tax_ids = [1, 2];

    const data = models.loadConnectedData(rawData);
    const orderLine = data["pos.order.line"][0];
    orderLine.qty = 1;
    orderLine.price_unit = 115.0; // price includes 15% tax
    const lineTax = orderLine.prices;
    // priceWithoutTax: 115 / 1.15 = 100, 25% tax = 25, priceWithTax = 115 + 25 = 140
    expect(lineTax.total_excluded).toBe(100.0);
    expect(lineTax.total_included).toBe(140.0);
    expect(lineTax.taxes_data[0].tax_amount).toBe(15.0);
    expect(lineTax.taxes_data[1].tax_amount).toBe(25.0);
});

test("[get quantityStr] Base test", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const data = models.loadConnectedData(getAllPricesData());
    const orderLine = data["pos.order.line"][0];
    const qtyStr = orderLine.quantityStr; // Test with qty = 2
    expect(qtyStr.qtyStr).toBe("2");
    expect(qtyStr.unitPart).toBe("2");
    expect(qtyStr.decimalPoint).toBe(".");
    expect(qtyStr.decimalPart).toBe("");

    orderLine.qty = 2.5; // Test with qty = 2.5
    const updatedQtyStr = orderLine.quantityStr;
    expect(updatedQtyStr.qtyStr).toBe("2.50");
    expect(updatedQtyStr.unitPart).toBe("2");
    expect(updatedQtyStr.decimalPoint).toBe(".");
    expect(updatedQtyStr.decimalPart).toBe("50");
});

test("[setQuantity] Base test", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const data = models.loadConnectedData(getAllPricesData());
    const orderLine = data["pos.order.line"][0];
    orderLine.setQuantity(2.77);
    expect(orderLine.qty).toBe(2.77);
    orderLine.setQuantity(2.779);
    expect(orderLine.qty).toBe(2.78);
    orderLine.setQuantity(2.771);
    expect(orderLine.qty).toBe(2.77);

    const comboOrderline = data["pos.order.line"][1];
    const comboChild1 = data["pos.order.line"][2];
    const comboChild2 = data["pos.order.line"][3];
    expect(comboOrderline.qty).toBe(1);
    expect(comboChild1.qty).toBe(2);
    expect(comboChild2.qty).toBe(1);
    expect(comboOrderline.price_unit).toBe(0);
    expect(comboChild1.price_unit).toBe(1);
    expect(comboChild2.price_unit).toBe(8);
    comboOrderline.setQuantity(3, true);
    expect(comboOrderline.qty).toBe(3);
    expect(comboChild1.qty).toBe(6);
    expect(comboChild2.qty).toBe(3);
    expect(comboOrderline.price_unit).toBe(0);
    expect(comboChild1.price_unit).toBe(1);
    expect(comboChild2.price_unit).toBe(8);
    comboOrderline.setQuantity(2, true);
    expect(comboOrderline.qty).toBe(2);
    expect(comboChild1.qty).toBe(4);
    expect(comboChild2.qty).toBe(2);
    expect(comboOrderline.price_unit).toBe(0);
    expect(comboChild1.price_unit).toBe(1);
    expect(comboChild2.price_unit).toBe(8);
});

test("[canBeMergedWith]: Base test", async () => {
    const store = await setupPosEnv();
    // Test with different products
    const order = await getFilledOrder(store);
    const line1 = order.lines[0];
    const line2 = order.lines[1];
    expect(line1.canBeMergedWith(line2)).toBe(false);
    // Test with same product, same price, same qty, no discount, different name
    line2.product_id = line1.product_id;
    expect(line1.canBeMergedWith(line2)).toBe(false);
    // Test with same product, same price, same qty, no discount, same name
    line2.setFullProductName("TEST");
    expect(line1.canBeMergedWith(line2)).toBe(true);
    // Test with different note
    line1.setNote("Test note");
    expect(line1.canBeMergedWith(line2)).toBe(false);
    // Test with same note
    line2.setNote("Test note");
    expect(line1.canBeMergedWith(line2)).toBe(true);
    // Test with discount applied
    line1.setDiscount(10.0);
    expect(line1.canBeMergedWith(line2)).toBe(false);
    // Test with same discount
    line2.setDiscount(10.0);
    expect(line1.canBeMergedWith(line2)).toBe(true);
    // Test with different price unit
    line2.price_unit = line1.price_unit + 1;
    line2.price_type = "manual";
    expect(line1.canBeMergedWith(line2)).toBe(false);
    // Test to merge lines
    line1.merge(line2);
    expect(line1.qty).toBe(5);
});

describe("Test taxes after fiscal position", () => {
    test("Orderline containing a taxed product", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const dataDict = getAllPricesData();
        dataDict["pos.order"][0]["fiscal_position_id"] = 2;
        const data = models.loadConnectedData(dataDict);
        const orderLine = data["pos.order.line"][0];
        const lineValues = orderLine.prepareBaseLineForTaxesComputationExtraValues();
        expect(lineValues.tax_ids.length).toBe(0);
    });
    test("Taxed Orderline orderline after fiscal position", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const dataDict = getAllPricesData();
        dataDict["pos.order"][0]["fiscal_position_id"] = 1;
        const data = models.loadConnectedData(dataDict);
        // Taxed order line
        const orderLine = data["pos.order.line"][0];
        // Taxed Product
        const taxedProductLineValues = orderLine.prepareBaseLineForTaxesComputationExtraValues();
        expect(taxedProductLineValues.tax_ids.length).toBe(1);
        // Non Taxed Product
        orderLine.product_id.taxes_id = [];
        const nonTaxedProductlineValues = orderLine.prepareBaseLineForTaxesComputationExtraValues();
        expect(nonTaxedProductlineValues.tax_ids.length).toBe(1);
    });
    test("Non-taxed orderline after fiscal position", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const dataDict = getAllPricesData();
        dataDict["pos.order"][0]["fiscal_position_id"] = 1;
        const data = models.loadConnectedData(dataDict);
        const orderLine = data["pos.order.line"][0];
        // Non taxed order line
        orderLine.tax_ids = [];
        // Taxed product
        const taxedProductLineValues = orderLine.prepareBaseLineForTaxesComputationExtraValues();
        expect(taxedProductLineValues.tax_ids.length).toBe(0);
        orderLine.product_id.taxes_id = [];
        // Non Taxed product
        const nonTaxedProductlineValues = orderLine.prepareBaseLineForTaxesComputationExtraValues();
        expect(nonTaxedProductlineValues.tax_ids.length).toBe(0);
    });
});
