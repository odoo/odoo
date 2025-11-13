import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";

definePosModels();

test("getOrderlineData", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const adapter = new CustomerDisplayPosAdapter();
    adapter.formatOrderData(order);

    expect(adapter.data.lines).toHaveLength(2);
    expect(adapter.data.lines[0].isSelected).toBe(false);
    expect(adapter.data.lines[1].isSelected).toBe(true);
});
