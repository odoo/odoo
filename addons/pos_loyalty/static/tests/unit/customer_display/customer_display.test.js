import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { setupPosEnv, mountCustomerDisplayWithOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("customer display UI renders loyalty points stats", async () => {
    await setupPosEnv();
    await mountCustomerDisplayWithOrder({
        amount: "$\u00a02,972.75",
        loyaltyData: [
            {
                couponId: 101,
                points: {
                    won: 25,
                    spent: 10,
                    total: 65,
                    balance: 50,
                    name: "Loyalty Points",
                },
            },
        ],
    });

    expect(queryOne(".loyalty-points-title")).toHaveText("Loyalty Points");
    expect(queryOne(".loyalty-points-balance")).toHaveText("50");
    expect(queryOne(".loyalty-points-won")).toHaveText("+ 25");
    expect(queryOne(".loyalty-points-spent")).toHaveText("- 10");
    expect(queryOne(".loyalty-points-total")).toHaveText("65");
});
