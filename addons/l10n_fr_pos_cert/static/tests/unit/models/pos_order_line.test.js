import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("showOldUnitPrice", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const line = order.getSelectedOrderline();
    expect(line.showOldUnitPrice).toBe(false);

    line.price_type = "manual";
    expect(line.showOldUnitPrice).toBe(true);

    line.is_reward_line = true;
    expect(line.showOldUnitPrice).toBe(false);
    line.is_reward_line = false;

    line.settled_order_id = 1;
    expect(line.showOldUnitPrice).toBe(false);
    line.settled_order_id = false;

    line.settled_invoice_id = 1;
    expect(line.showOldUnitPrice).toBe(false);
    line.settled_invoice_id = false;

    line.sale_order_origin_id = 1;
    expect(line.showOldUnitPrice).toBe(false);
    line.sale_order_origin_id = false;

    line.event_ticket_id = 1;
    expect(line.showOldUnitPrice).toBe(false);
    line.event_ticket_id = false;

    store.config.module_pos_discount = true;
    store.config.discount_product_id = line.product_id;
    expect(line.showOldUnitPrice).toBe(false);
    store.config.discount_product_id = false;

    store.config._pos_special_display_products_ids = [line.product_id.product_tmpl_id.id];
    expect(line.showOldUnitPrice).toBe(false);
    store.config._pos_special_display_products_ids = [];

    store.config.deposit_product_id = line.product_id;
    expect(line.showOldUnitPrice).toBe(false);
    store.config.deposit_product_id = false;

    const tipProduct = store.config.tip_product_id;
    line.product_id = tipProduct;
    expect(line.showOldUnitPrice).toBe(false);
});
