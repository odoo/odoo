import { test, expect } from "@odoo/hoot";
import { createAttribute, createAttributeValue, setupPosEnv } from "../utils";
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
    expect(item1Line.price_unit).toBe(100);

    expect(item3Line.getQuantity()).toBe(2);
    expect(item3Line.price_unit).toBe(200);

    // Total = (0*2) + (100*2) + (200*2) = 0 + 200 + 400 = 600.
    // Tax 25% -> 600 * 1.25 = 750.
    expect(order.priceIncl).toBe(750);

    order.setPricelist(pricelist90);

    expect(comboParentLine.price_unit).toBe(0);
    expect(item1Line.price_unit).toBe(100);

    expect(item3Line.price_unit).toBeGreaterThan(0);

    expect(order.priceIncl).not.toBe(750);
    expect(order.priceIncl).toBeGreaterThan(0);
});

test("extra price is shown on the child lines that are actually paid for", async () => {
    const store = await setupPosEnv();
    const template = store.models["product.template"].get(7);
    const combo = store.models["product.combo"].get(1);
    const [freeChoice, paidChoice] = combo.combo_item_ids;

    combo.qty_free = 1;
    combo.base_price = 50;

    const size = createAttribute(store, "Size", "radio", "dynamic");
    const large = createAttributeValue(store, size, "Large", { priceExtra: 10 });
    paidChoice.product_id.product_template_attribute_value_ids = [large];

    const order = store.addNewOrder();
    order.setPricelist(false);
    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: freeChoice, qty: 1 }],
                [
                    {
                        combo_item_id: paidChoice,
                        qty: 1,
                        configuration: { attribute_value_ids: [large.id] },
                    },
                ],
            ],
            qty: 1,
        },
        order
    );

    const parentLine = order.lines.find((l) => l.product_id.product_tmpl_id.id === template.id);
    const freeLine = parentLine.combo_line_ids.find((l) => l.combo_item_id.id === freeChoice.id);
    const paidLine = parentLine.combo_line_ids.find((l) => l.combo_item_id.id === paidChoice.id);

    expect(freeLine.price_unit).toBe(100);
    expect(paidLine.price_unit).toBe(95);

    expect(freeLine.currencyDisplayPrice).toBe("");
    expect(paidLine.currencyDisplayPrice).toBe("$ 118.75");
    expect(parentLine.displayPrice - paidLine.comboExtraDisplayPrice).toBe(125);

    order.setPricelist(false);
    expect(paidLine.price_extra).toBe(10);
    expect(paidLine.currencyDisplayPrice).toBe("$ 118.75");

    paidLine.setDiscount(50);
    expect(paidLine.currencyDisplayPrice).toBe("$ 59.38");
    paidLine.setDiscount(100);
    expect(paidLine.currencyDisplayPrice).toBe("");

    paidLine.setDiscount(0);
    paidLine.tax_ids = [
        store.models["account.tax"].create({
            name: "Fixed 15",
            amount: 15,
            amount_type: "fixed",
            price_include: false,
            include_base_amount: false,
            is_base_affected: true,
            has_negative_factor: false,
            company_id: 250,
            sequence: 1,
            tax_group_id: 1,
        }),
    ];
    expect(paidLine.currencyDisplayPrice).toBe("$ 95");
});
