import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { expectFormattedPrice, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import {
    getFilledOrderForPriceCheck,
    createTax,
    createFiscalPosition,
    getSingleProductOrder,
    setFiscalPosition,
} from "./utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

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

test("FiscalPositionNoTax: fiscal position no tax", async () => {
    const store = await setupPosEnv();
    const includedTax = createTax(store, "Tax 15%", 15, true);
    const fiscalPosition = createFiscalPosition(store, "No Tax");
    includedTax.update({ fiscal_position_ids: [fiscalPosition] });
    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fiscalPosition];

    const order = await getSingleProductOrder(store, "Test Product", 100, [includedTax]);
    expect(order.displayPrice).toBe(100);

    setFiscalPosition(order, fiscalPosition);
    expect(order.displayPrice).toBe(100);
    expect(order.lines[0].discount).toBe(undefined);
});

test("FiscalPositionIncl: fiscal position incl", async () => {
    const store = await setupPosEnv();
    const taxIncl20 = createTax(store, "Tax incl.20%", 20, true);
    const taxIncl10 = createTax(store, "Tax incl.10%", 10, true);
    const taxExcl10 = createTax(store, "Tax excl.10%", 10, false);
    const fpInclToIncl = createFiscalPosition(store, "Incl. to Incl.", [taxIncl10], {
        [taxIncl20.id]: [taxIncl10.id],
    });
    const fpInclToExcl = createFiscalPosition(store, "Incl. to Excl.", [taxExcl10], {
        [taxIncl20.id]: [taxExcl10.id],
    });
    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fpInclToIncl, fpInclToExcl];

    const order = await getSingleProductOrder(store, "Test Product 1", 100, [taxIncl20]);
    expect(order.displayPrice).toBe(100);

    setFiscalPosition(order, fpInclToIncl);
    expect(order.displayPrice).toBe(100);

    setFiscalPosition(order, fpInclToExcl);
    expect(order.displayPrice).toBe(110);
});

test("FiscalPositionExcl: fiscal position excl", async () => {
    const store = await setupPosEnv();
    const taxExcl20 = createTax(store, "Tax excl.20%", 20, false);
    const taxExcl10 = createTax(store, "Tax excl.10%", 10, false);
    const taxIncl10 = createTax(store, "Tax incl.10%", 10, true);
    const fpExclToExcl = createFiscalPosition(store, "Excl. to Excl.", [taxExcl10], {
        [taxExcl20.id]: [taxExcl10.id],
    });
    const fpExclToIncl = createFiscalPosition(store, "Excl. to Incl.", [taxIncl10], {
        [taxExcl20.id]: [taxIncl10.id],
    });
    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fpExclToExcl, fpExclToIncl];

    const order = await getSingleProductOrder(store, "Test Product 2", 100, [taxExcl20]);
    expect(order.displayPrice).toBe(120);

    setFiscalPosition(order, fpExclToExcl);
    expect(order.displayPrice).toBe(110);

    setFiscalPosition(order, fpExclToIncl);
    expect(order.displayPrice).toBe(100);
});

test("FiscalPositionNoTaxRefund: fiscal position no tax refund", async () => {
    const store = await setupPosEnv();
    const includedTax = createTax(store, "Tax 15%", 15, true);
    const zeroTax = createTax(store, "Tax 0%", 0, true);
    const fiscalPosition = createFiscalPosition(store, "No Tax", [zeroTax], {
        [includedTax.id]: [zeroTax.id],
    });
    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fiscalPosition];

    const order = await getSingleProductOrder(store, "Product Test", 100, [includedTax]);
    expect(order.displayPrice).toBe(100);
    setFiscalPosition(order, fiscalPosition);
    expect(order.displayPrice).toBe(100);
    order.state = "paid";

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });
    await ticketScreen.onDoRefund();

    const refundOrder = store.getOrder();
    expect(refundOrder.fiscal_position_id).toBe(fiscalPosition);
    expect(refundOrder.displayPrice).toBe(-100);
});
