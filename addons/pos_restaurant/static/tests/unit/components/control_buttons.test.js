import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";

definePosModels();

test("clickPrintBill syncs the order so it isn't lost on a data reload", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    store.printReceipt = async () => true;

    const component = await mountWithCleanup(ControlButtons, {});
    expect(order.isSynced).toBe(false);

    await component.clickPrintBill();

    expect(order.isSynced).toBe(true);
    expect(order.isDirty()).toBe(false);
    expect(store.getPendingOrder().orderToCreate).toHaveLength(0);
});
