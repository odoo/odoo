import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

import { renderReceipt } from "@point_of_sale/../tests/unit/receipt_utils";
import {
    expectLoyaltyReceiptPayload,
    expectLoyaltyTicketData,
} from "@pos_loyalty/../tests/unit/receipt_utils";

definePosModels();

test("test loyalty related data in order receipt", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const partner = store.models["res.partner"].get(3);

    expect(order.partner_id).toBeEmpty();

    let { data, ticket } = renderReceipt(store, order);
    expectLoyaltyReceiptPayload(data, { loyaltyPointsData: [] });
    order.partner_id = partner;
    ({ data, ticket } = renderReceipt(store, order));
    const expectedLoyaltyData = [
        {
            name: "Points",
            type: "Won:",
            points: 1,
        },
        {
            name: "Points",
            type: "Balance:",
            points: 1,
        },
        {
            name: "Points",
            type: "Won:",
            points: 5,
        },
        {
            name: "Points",
            type: "Balance:",
            points: 5,
        },
    ];
    expectLoyaltyReceiptPayload(data, {
        loyaltyPointsData: expectedLoyaltyData,
    });
    expectLoyaltyTicketData(ticket, {
        loyaltyPointsData: expectedLoyaltyData,
    });
});
