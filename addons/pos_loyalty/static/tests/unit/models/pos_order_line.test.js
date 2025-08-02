import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

let store;
let models;

beforeEach(async () => {
    store = await setupPosEnv();
    models = store.models;
});

describe("pos.order.line - loyalty", () => {
    test("getEWalletGiftCardProgramType returns correct program type", async () => {
        const program = models["loyalty.program"].get(2);

        const line = models["pos.order.line"].create({});
        line.update({ _e_wallet_program_id: program });

        expect(line.getEWalletGiftCardProgramType()).toBe(`${program.program_type}`);
    });

    test("ignoreLoyaltyPoints returns true when program mismatches", async () => {
        const programA = models["loyalty.program"].create({
            id: 1,
            program_type: "ewallet",
        });
        const programB = models["loyalty.program"].create({
            id: 2,
            program_type: "ewallet",
        });

        const line = models["pos.order.line"].create({});
        line.update({ _e_wallet_program_id: programB });
        expect(line.ignoreLoyaltyPoints({ program: programA })).toBe(true);
    });

    test("isGiftCardOrEWalletReward identifies reward lines properly", async () => {
        const program = models["loyalty.program"].get(2);
        const card = models["loyalty.card"].get(1);
        card.program_id = program;

        const line = models["pos.order.line"].create({ is_reward_line: true });
        line.coupon_id = card;

        expect(line.isGiftCardOrEWalletReward()).toBe(true);
    });

    test("returns formatted balance with correct currency", async () => {
        const program = models["loyalty.program"].get(3);
        const card = models["loyalty.card"].get(1);
        card.program_id = program;

        const order = store.addNewOrder();
        const product = models["product.template"].get(1);

        const line = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                is_reward_line: true,
                coupon_id: card,
            },
            order
        );

        const balance = line.getGiftCardOrEWalletBalance();

        expect(typeof balance).toBe("string");
        expect(balance).toMatch(new RegExp(`${card.points}`));
    });

    test("getDisplayClasses marks reward lines italic", async () => {
        const line = models["pos.order.line"].create({
            is_reward_line: true,
        });
        expect(line.getDisplayClasses()["fst-italic"]).toBe(true);
    });
});
