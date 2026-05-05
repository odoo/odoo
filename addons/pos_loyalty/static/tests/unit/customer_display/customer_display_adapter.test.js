import { expect, test } from "@odoo/hoot";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("formatOrderData includes loyalty points for the customer display", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.uiState.couponPointChanges = {
        1: {
            coupon_id: 1,
            program_id: 1,
            points: 25,
        },
        ignoredGiftCard: {
            coupon_id: 3,
            program_id: 3,
            points: 50,
        },
    };

    const adapter = new CustomerDisplayPosAdapter();
    adapter.formatOrderData(order);

    expect(adapter.data.loyaltyData).toHaveLength(1);
    expect(adapter.data.loyaltyData[0].couponId).toBe("1");
    expect(adapter.data.loyaltyData[0].points).toMatchObject({
        won: 25,
        spent: 0,
        total: 75,
        balance: 50,
        name: "Points",
    });
});

test("formatOrderData keeps detailed loyalty stats used by customer display UI", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.getLoyaltyPoints = () => [
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
    ];

    const adapter = new CustomerDisplayPosAdapter();
    adapter.formatOrderData(order);

    expect(adapter.data.loyaltyData).toHaveLength(1);
    expect(adapter.data.loyaltyData[0]).toMatchObject({
        couponId: 101,
        points: {
            won: 25,
            spent: 10,
            total: 65,
            balance: 50,
            name: "Loyalty Points",
        },
    });
});
