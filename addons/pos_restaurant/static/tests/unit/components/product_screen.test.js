import { test, expect } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

test("select existing order when preset requires order name", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.floating_order_name = "The Other Order";
    order.preset_id = 2;
    order.preset_time = luxon.DateTime.now();
    const order2 = await getFilledOrder(store);
    store.setOrder(order2);
    await mountWithCleanup(ProductScreen, { props: { orderUuid: order2.uuid } });

    const namePreset = store.models["pos.preset"].get(3);
    namePreset.use_timing = true;
    await click("button:contains(In)");
    // Select namePreset preset
    await waitFor(".modal-title:contains(Select preset)");
    await click("button:contains(Name Required Preset)");
    await waitFor(".modal-title:contains(Edit Order Name)");
    await animationFrame();
    // Select Existing Order
    await click("button:contains(The Other Order)");
    await animationFrame();
    expect(".modal-dialog").toHaveCount(0);
    expect(store.models["pos.order"].get(order2.id)).toBeEmpty();
    const currentOrder = store.getOrder();
    expect(currentOrder.id).toBe(order.id);
    expect(currentOrder.preset_id.id).toBe(2);
    expect(currentOrder.getName()).toBe("The Other Order");
});
