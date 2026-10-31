import { test, expect } from "@odoo/hoot";
import { expectFormattedPrice, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { getFilledOrderForPriceCheck } from "./utils";

definePosModels();

test("Prices includes", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderForPriceCheck(store);
    const details = order.prices.taxDetails;
    const line1 = order.lines[0].prices;
    const line2 = order.lines[1].prices;

    // Order prices
    expect(details.base_amount).toBe(1100);
    expect(details.tax_amount).toBe(290);
    expect(details.total_amount).toBe(1390);

    // First line (25% on 1000)
    expect(line1.total_included).toBe(1250);
    expect(line1.total_excluded).toBe(1000);
    expect(line1.taxes_data[0].tax_amount).toBe(250);
    expect(line1.taxes_data[0].tax.amount).toBe(25);

    // Second line (15% + 25% on 100)
    expect(line2.total_included).toBe(140);
    expect(line2.total_excluded).toBe(100);
    expect(line2.taxes_data[0].tax_amount).toBe(15);
    expect(line2.taxes_data[0].tax.amount).toBe(15);
    expect(line2.taxes_data[1].tax_amount).toBe(25);
    expect(line2.taxes_data[1].tax.amount).toBe(25);

    // Formatted prices
    expectFormattedPrice(order.currencyDisplayPrice, "$ 1,390.00");
    expectFormattedPrice(order.currencyAmountTaxes, "$ 290.00");
    expectFormattedPrice(order.lines[0].currencyDisplayPrice, "$ 1,250.00");
    expectFormattedPrice(order.lines[0].currencyDisplayPriceUnit, "$ 1,250.00");
    expectFormattedPrice(order.lines[0].currencyDisplayPriceUnitExcl, "$ 1,000.00");
    expectFormattedPrice(order.lines[1].currencyDisplayPrice, "$ 140.00");
    expectFormattedPrice(order.lines[1].currencyDisplayPriceUnit, "$ 140.00");
    expectFormattedPrice(order.lines[1].currencyDisplayPriceUnitExcl, "$ 100.00");
});

test("Prices excludes", async () => {
    const store = await setupPosEnv();
    store.config.iface_tax_included = "subtotal";
    const order = await getFilledOrderForPriceCheck(store);

    // Formatted prices
    expectFormattedPrice(order.currencyDisplayPrice, "$ 1,100.00");
    expectFormattedPrice(order.lines[0].currencyDisplayPrice, "$ 1,000.00");
    expectFormattedPrice(order.lines[0].currencyDisplayPriceUnit, "$ 1,000.00");
    expectFormattedPrice(order.lines[1].currencyDisplayPrice, "$ 100.00");
    expectFormattedPrice(order.lines[1].currencyDisplayPriceUnit, "$ 100.00");
});

test("Combo prices incl and excl", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const template = store.models["product.template"].get(7);
    const comboProduct = store.models["product.combo.item"].get(1);

    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [[{ combo_item_id: comboProduct, qty: 1 }]],
            qty: 1,
        },
        order
    );
    order.setOrderPrices();

    const [comboParentLine, comboChildLine] = order.lines;

    expect(comboParentLine.comboTotalPrice).toBe(3.75);
    expect(comboParentLine.comboTotalPriceWithoutTax).toBe(3);

    expect(comboChildLine.comboTotalPrice).toBe(3.75);
    expect(comboChildLine.comboTotalPriceWithoutTax).toBe(3);
});

test("Unit price keeps more digits than the Product Price precision", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    order.pricelist_id = false;
    // 25% tax excluded, Product Price precision is 2
    const template = store.models["product.template"].get(15);
    template.list_price = 10.004;
    template.product_variant_ids[0].lst_price = 10.004;

    const line = await store.addLineToOrder({ product_tmpl_id: template, qty: 2 }, order);

    expect(line.price_unit).toBe(10.004);
    expect(line.prices.total_excluded).toBe(20.01);
    expect(line.prices.total_included).toBe(25.01);
});
