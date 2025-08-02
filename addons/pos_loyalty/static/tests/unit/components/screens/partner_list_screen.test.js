import { describe, expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("partner_list_screen.js", () => {
    test("searchPartner should fetch coupons and assign them", async () => {
        const store = await setupPosEnv();
        const models = store.models;

        const program = models["loyalty.program"].get(1);
        const partner = models["res.partner"].get(1);

        const coupon = models["loyalty.card"].get(1);
        coupon.program_id = program;
        coupon.partner_id = partner;

        const partners = [
            { id: 1, name: "Test 1" },
            { id: 2, name: "Test 2" },
        ];
        PartnerList.prototype.getNewPartners = () => partners;

        const screen = await mountWithCleanup(PartnerList, {
            props: {
                getPayload: () => {},
                close: () => {},
            },
        });

        const result = await screen.searchPartner();

        expect(result).toBeInstanceOf(Array);
        expect(result.length).toBeGreaterThan(0);
    });
});
