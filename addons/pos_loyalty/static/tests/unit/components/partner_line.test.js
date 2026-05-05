import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("_getLoyaltyPointsRepr", async () => {
    const store = await setupPosEnv();
    const models = store.models;

    const partner = models["res.partner"].get(1);

    const loyaltyCards = [
        {
            points: 10,
            program_id: {
                program_type: "loyalty",
                portal_point_name: "Points",
                name: "Loyalty Program",
            },
        },
        {
            points: 25,
            program_id: {
                program_type: "ewallet",
                portal_point_name: "Points",
                name: "E-Wallet Program",
            },
        },
        {
            points: 15,
            program_id: {
                program_type: "gift_card",
                portal_visible: true,
                portal_point_name: "Gift Card Points",
                name: "GC Program",
            },
        },
    ];

    const component = await mountWithCleanup(PartnerLine, {
        props: {
            partner,
            close: () => {},
            isSelected: false,
            isBalanceDisplayed: true,
            onClickEdit: () => {},
            onClickUnselect: () => {},
            onClickPartner: () => {},
            onClickOrders: () => {},
        },
        env: {
            ...store.env,
            utils: {
                formatCurrency: (val) => `$${val.toFixed(2)}`,
            },
        },
    });

    const results = loyaltyCards.map((card) => component._getLoyaltyPointsRepr(card));

    expect(results[0]).toBe("10.00 Points");
    expect(results[1]).toBe("E-Wallet Program: $25.00");
    expect(results[2]).toMatch("15.00 Gift Card Points");
});
