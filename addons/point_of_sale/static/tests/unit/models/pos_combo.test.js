import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("combo price remains consistent when recomputing prices", async () => {
    const store = await setupPosEnv();
    const pricelistA = store.models["product.pricelist"].get(1);
    const pricelist90 = store.models["product.pricelist"].get(3);

    const template = store.models["product.template"].get(7);
    const comboItem1 = store.models["product.combo.item"].get(1);
    const comboItem3 = store.models["product.combo.item"].get(3);

    const order = store.addNewOrder();
    order.setPricelist(pricelistA);

    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: comboItem1, qty: 1 }],
                [{ combo_item_id: comboItem3, qty: 1 }],
            ],
            qty: 2,
        },
        order
    );

    const comboParentLine = order.lines.find(
        (l) => l.product_id.product_tmpl_id.id === template.id
    );

    expect(comboParentLine.getQuantity()).toBe(2);
    expect(comboParentLine.price_unit).toBe(0);

    const childLines = order.lines.filter((l) => l.combo_parent_id?.uuid === comboParentLine.uuid);
    expect(childLines).toHaveLength(2);

    const item1Line = childLines.find((l) => l.combo_item_id.id === 1);
    const item3Line = childLines.find((l) => l.combo_item_id.id === 3);

    expect(item1Line.getQuantity()).toBe(2);
    expect(item1Line.price_unit).toBe(3);

    expect(item3Line.getQuantity()).toBe(2);
    expect(item3Line.price_unit).toBe(200);

    // Total = (0*2) + (3*2) + (200*2) = 0 + 6 + 400 = 406.
    // Tax 25% -> 406 * 1.25 = 507.5.
    expect(order.priceIncl).toBe(507.5);

    order.setPricelist(pricelist90);

    expect(comboParentLine.price_unit).toBe(0);
    expect(item1Line.price_unit).toBe(100);

    expect(item3Line.price_unit).toBeGreaterThan(0);

    expect(order.priceIncl).not.toBe(507.5);
    expect(order.priceIncl).toBeGreaterThan(0);
});

test("extra price is shown on the child lines that are actually paid for", async () => {
    const store = await setupPosEnv();
    const template = store.models["product.template"].get(7);
    const combo = store.models["product.combo"].get(1);
    const [freeChoice, paidChoice] = combo.combo_item_ids;
    // 1 free unit, and a base price below the price of the combo (100) so that the
    // free child line ends up with a higher unit price than the paid one.
    combo.qty_free = 1;
    combo.base_price = 50;

    const order = store.addNewOrder();
    order.setPricelist(false);
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: freeChoice, qty: 1 }],
                [{ combo_item_id: paidChoice, qty: 1 }],
            ],
            qty: 1,
        },
        order
    );

    const parentLine = order.lines.find((l) => l.product_id.product_tmpl_id.id === template.id);
    const freeLine = parentLine.combo_line_ids.find((l) => l.combo_item_id.id === freeChoice.id);
    const paidLine = parentLine.combo_line_ids.find((l) => l.combo_item_id.id === paidChoice.id);

    // The free line carries the price of the combo itself, the paid one the base
    // price of the choice plus its 35 surcharge.
    expect(freeLine.price_unit).toBe(100);
    expect(paidLine.price_unit).toBe(85);

    // The free unit is granted to the first line, whatever their prices are.
    expect(freeLine.comboExtraQuantity).toBe(0);
    expect(freeLine.comboExtraPrice).toBe(0);
    expect(freeLine.currencyComboExtraPrice).toBe("");
    expect(paidLine.comboExtraQuantity).toBe(1);
    expect(paidLine.comboExtraPrice).toBe(85);

    // Extras are displayed with taxes included, like the parent line, so that what
    // remains on the parent line is the price of the combo itself (100 + 25% tax).
    expect(paidLine.currencyComboExtraPrice).toBe("+ $ 106.25");
    expect(parentLine.displayPrice - paidLine.comboExtraDisplayPrice).toBe(125);
});

test("extra price of a combo child follows the discount of the line", async () => {
    const store = await setupPosEnv();
    const template = store.models["product.template"].get(7);
    const combo = store.models["product.combo"].get(1);
    const [freeChoice, paidChoice] = combo.combo_item_ids;
    combo.qty_free = 1;

    const order = store.addNewOrder();
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: freeChoice, qty: 1 }],
                [{ combo_item_id: paidChoice, qty: 1 }],
            ],
            qty: 1,
        },
        order
    );

    const parentLine = order.lines.find((l) => l.product_id.product_tmpl_id.id === template.id);
    const paidLine = parentLine.combo_line_ids.find((l) => l.combo_item_id.id === paidChoice.id);
    const extraPrice = paidLine.comboExtraDisplayPrice;

    paidLine.setDiscount(50);
    expect(paidLine.comboExtraDisplayPrice).toBe(store.currency.round(extraPrice / 2));

    paidLine.setDiscount(100);
    expect(paidLine.currencyComboExtraPrice).toBe("");
});
