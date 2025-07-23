import { describe, test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("partner_line.js", () => {
    test("_getLoyaltyPointsRepr", async () => {
        const store = await setupPosEnv();
        const models = store.models;

        const partner = models["res.partner"].get(1);
        // Get first 3 loyalty cards and map them with program
        const loyaltyCards = models["loyalty.card"]
            .getAll()
            .slice(0, 3)
            .map((element) => ({
                id: element.id,
                points: element.points,
                partner_id: partner.id,
                program_id: models["loyalty.program"].get(element.id),
            }));

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
});
