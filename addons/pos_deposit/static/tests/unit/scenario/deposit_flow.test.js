import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("deposit lines follow their product", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false, module_pos_deposit: true });
    const order = store.getOrder();
    const template = (id) => store.models["product.template"].get(id);
    const comboItem = (id) => store.models["product.combo.item"].get(id);

    const product = await store.addLineToCurrentOrder({ product_tmpl_id: template(5) });
    await store.addLineToCurrentOrder({ product_tmpl_id: template(5) });
    await animationFrame();
    expect(Utils.getOrderlineNames()).toEqual(["TEST", "Deposit"]);
    expect(product.depositLine.qty).toBe(2);

    product.depositLine.setQuantity(5);
    expect(product.qty).toBe(5);

    await store.addLineToCurrentOrder({ product_tmpl_id: template(9100) });
    expect(order.totalItemQuantity).toBe(5);

    const combo = await store.addLineToCurrentOrder({
        product_tmpl_id: template(7),
        payload: [
            [
                { combo_item_id: comboItem(1), qty: 1 },
                { combo_item_id: comboItem(4), qty: 1 },
            ],
            [],
        ],
    });
    await animationFrame();
    expect(Utils.getOrderlineNames()).toEqual([
        "TEST",
        "Deposit",
        "Deposit",
        "Product combo",
        "Wood chair",
        "Deposit",
        "Steel desk",
        "Deposit",
    ]);

    combo.setQuantity(2);
    const depositLines = order.lines.filter((line) => line.deposit_main_line_id);
    expect(depositLines.map((line) => line.qty)).toEqual([5, 2, 2]);

    order.removeOrderline(product.depositLine);
    order.removeOrderline(combo);
    await animationFrame();
    expect(Utils.getOrderlineNames()).toEqual(["Deposit"]);
});
