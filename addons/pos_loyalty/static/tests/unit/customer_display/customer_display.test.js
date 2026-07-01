import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    setupCustomerDisplay,
    CustomerDisplayAssertions as Assert,
} from "@point_of_sale/../tests/unit/customer_display/utils";

definePosModels();

test("[Old Tour] test_customer_display_loyalty_points", async () => {
    const [store, order] = await setupCustomerDisplay();
    const product = store.models["product.template"].get(5);
    await store.addLineToCurrentOrder({ product_tmpl_id: product });
    await Assert.hasOrderLine({ productName: "TEST", price: "$ 3.45" });
    await Assert.hasOrderLine({ productName: "TEST", price: "$ -3.45" }); // Free line

    // Add Loyalty
    order.uiState.couponPointChanges = {
        1: {
            coupon_id: 1,
            program_id: 1,
            points: 25,
        },
    };
    const partner = store.models["res.partner"].get(3);
    order.setPartner(partner);
    await Assert.hasOrderlineCount(2);

    // Loyalty stats on the order
    const loyaltyStats = order.getLoyaltyPoints();
    expect(loyaltyStats).toHaveLength(1);
    expect(loyaltyStats[0].points.name).toBe("Points");
    expect(loyaltyStats[0].points.won).toBe(25);
    expect(loyaltyStats[0].points.balance).toBe(10);

    // Loyalty stats on customer display
    expect(".loyalty-points-title").toHaveText("Points");
    expect(".loyalty-points-balance").toHaveText("10");
    expect(".loyalty-points-won").toHaveText("+ 25");
    expect(".loyalty-points-total").toHaveText("35");
});
