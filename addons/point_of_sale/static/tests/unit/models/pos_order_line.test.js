import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

function getAllPricesData(otherData = {}) {
    return {
        "pos.order": [
            {
                id: 1,
                name: "Test Order",
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
        ],
        ...otherData,
    };
}

describe("pos.order.line", () => {
    test("[getAllPrices()] Base test", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const data = models.loadConnectedData(getAllPricesData());

        const lineTax = data["pos.order.line"][0].getAllPrices();
        expect(lineTax.priceWithTax).toBe(230.0);
        expect(lineTax.priceWithoutTax).toBe(200.0);
        expect(lineTax.taxesData[0].tax).toEqual(models["account.tax"].getFirst());
        expect(lineTax.taxDetails[1].base).toBe(200.0);
        expect(lineTax.taxDetails[1].amount).toBe(30.0);

        // Test with line qty = 0
        data["pos.order.line"][0].qty = 0;
        const zeroQtyLineTax = data["pos.order.line"][0].getAllPrices();
        expect(zeroQtyLineTax.priceWithTax).toBe(0.0);
        expect(zeroQtyLineTax.priceWithoutTax).toBe(0.0);
        expect(zeroQtyLineTax.tax).toBe(0.0);
        expect(Object.keys(zeroQtyLineTax.taxDetails).length).toBe(1);
    });

    test("[getAllPrices()] with discount applied", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const data = models.loadConnectedData(getAllPricesData());
        const orderLine = data["pos.order.line"][0];
        orderLine.setDiscount(10.0); // 10% discount
        const lineTax = orderLine.getAllPrices();
        // Prices with a discount of 10% applied: 230 * 0.9 = 207.0
        expect(lineTax.priceWithTax).toBe(207.0);
        expect(lineTax.priceWithoutTax).toBe(180.0);
        expect(lineTax.taxDetails[1].amount).toBe(27.0);
        // Price with a discount of 100% applied
        orderLine.setDiscount(100.0);
        const updatedLineTax = orderLine.getAllPrices();
        expect(updatedLineTax.priceWithoutTax).toBe(0.0);
        expect(updatedLineTax.priceWithTax).toBe(0.0);
        expect(updatedLineTax.tax).toBe(0.0);
        expect(updatedLineTax.taxDetails[1].amount).toBe(0.0);
    });

    test("[getAllPrices()] with multiple taxes settings", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const data = models.loadConnectedData(getAllPricesData());
        const orderLine = data["pos.order.line"][0];
        // Test with two taxes applied (15% and 25%)
        orderLine.tax_ids = [1, 2];
        orderLine.qty = 1;
        const lineTax = orderLine.getAllPrices();
        expect(lineTax.priceWithoutTax).toBe(100.0);
        expect(lineTax.priceWithTax).toBe(140.0);
        expect(lineTax.tax).toBe(40.0);
        expect(lineTax.taxDetails[1].amount).toBe(15.0);
        expect(lineTax.taxDetails[2].amount).toBe(25.0);

        // Test with "include_base_amount" and "include_base_amount" to true for both taxes
        models["account.tax"].get(1).include_base_amount = true;
        models["account.tax"].get(2).include_base_amount = true;
        const updatedLineTax = data["pos.order.line"][0].getAllPrices();
        expect(updatedLineTax.priceWithoutTax).toBe(100.0);
        expect(updatedLineTax.priceWithTax).toBe(143.75);
        expect(updatedLineTax.tax).toBe(43.75);
        expect(updatedLineTax.taxDetails[1].amount).toBe(15.0);
        expect(updatedLineTax.taxDetails[2].amount).toBe(28.75);

        // Test without any taxes
        orderLine.tax_ids = [];
        const noTaxLine = data["pos.order.line"][0].getAllPrices();
        expect(noTaxLine.priceWithoutTax).toBe(100.0);
        expect(noTaxLine.priceWithTax).toBe(100.0);
        expect(noTaxLine.tax).toBe(0.0);
        expect(Object.keys(noTaxLine.taxDetails).length).toBe(0);
    });

    test("[getAllPrices()] with fixed-amount tax", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const data = models.loadConnectedData(getAllPricesData());
        models["account.tax"].get(1).amount_type = "fixed";
        const orderLine = data["pos.order.line"][0];
        orderLine.qty = 3;
        orderLine.price_unit = 10.0;
        const lineTax = orderLine.getAllPrices();
        // 3 * 10 = 30, tax = 3 * 15 = 45
        expect(lineTax.priceWithoutTax).toBe(30.0);
        expect(lineTax.priceWithTax).toBe(75.0);
        expect(lineTax.tax).toBe(45.0);
        expect(lineTax.taxDetails[1].amount).toBe(45.0);
    });

    test("[getAllPrices()] with one price-included and one price-excluded tax", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const data = models.loadConnectedData(getAllPricesData());
        const orderLine = data["pos.order.line"][0];
        orderLine.tax_ids = [1, 2];
        orderLine.qty = 1;
        orderLine.price_unit = 115.0; // price includes 15% tax
        models["account.tax"].get(1).price_include = true;
        const lineTax = orderLine.getAllPrices();
        // priceWithoutTax: 115 / 1.15 = 100, 25% tax = 25, priceWithTax = 115 + 25 = 140
        expect(lineTax.priceWithoutTax).toBe(100.0);
        expect(lineTax.priceWithTax).toBe(140.0);
        expect(lineTax.tax).toBe(40.0);
        expect(lineTax.taxDetails[1].amount).toBe(15.0);
        expect(lineTax.taxDetails[2].amount).toBe(25.0);
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
        // Test to merge lines
        line1.merge(line2);
        expect(line1.qty).toBe(5);
    });

    test("Test taxes after fiscal position", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const dataDict = getAllPricesData();
        dataDict["pos.order"][0]["fiscal_position_id"] = 2;
        const data = models.loadConnectedData(dataDict);
        const orderLine = data["pos.order.line"][0];
        const lineValues = orderLine.prepareBaseLineForTaxesComputationExtraValues();
        expect(lineValues.tax_ids.length).toBe(0);
    });
});
