import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupCustomerDisplay,
    CustomerDisplayAssertions as Assert,
} from "@point_of_sale/../tests/unit/customer_display/utils";
import { deactivateAllProgramsExcept } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

test("[Old Tour] test_customer_display_loyalty_points", async () => {
    const [store, order] = await setupCustomerDisplay();
    // Isolate loyalty program 7 (nominative, earns 1 point per unit sold) so its
    // stats are the only ones shown on the customer display.
    deactivateAllProgramsExcept(store, [7]);

    const product = store.models["product.template"].get(5);
    await store.addLineToCurrentOrder({ product_tmpl_id: product });
    await Assert.hasOrderLine({ productName: "TEST", price: "$ 115.00" });

    // Add partner: card 4 already carries a 3-point balance on program 7.
    const partner = store.models["res.partner"].get(1);
    order.setPartner(partner);
    await Assert.hasOrderlineCount(1);

    // Loyalty stats on the order
    const program = store.models["loyalty.program"].get(7);
    expect(program.getEarnedPoints(order)).toBe(1);
    expect(program.getAvailablePoints(order)).toBe(3);
    expect(program.getNewBalance(order)).toBe(4);

    // Loyalty stats on customer display
    expect(".loyalty-points-title").toHaveText("Loyalty Program Future");
    expect(".loyalty-points-balance").toHaveText("3");
    expect(".loyalty-points-won").toHaveText("+ 1");
    expect(".loyalty-points-total").toHaveText("4");
});
