import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import {
    addProductLineToOrder,
    deactivateAllProgramsExcept,
} from "@pos_loyalty/../tests/unit/utils";
import "@pos_loyalty/app/customer_display/customer_display_adapter";

definePosModels();

test("formatOrderData serializes the loyalty breakdown for the customer display", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = store.addNewOrder();

    deactivateAllProgramsExcept(store, [2, 3, 7]);

    const partner = models["res.partner"].get(1);
    store.setPartnerToCurrentOrder(partner);
    await addProductLineToOrder(store, order, { qty: 1 });

    const adapter = new CustomerDisplayPosAdapter();
    adapter.formatOrderData(order);

    expect(adapter.data.loyaltyPrograms).toHaveLength(1);
    expect(adapter.data.loyaltyPrograms[0]).toEqual({
        id: 7,
        name: "Loyalty Program Future",
        won: 1,
        spent: 0,
        balance: 3,
        total: 4,
    });
});
