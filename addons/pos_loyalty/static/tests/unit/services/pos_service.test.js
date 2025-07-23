import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

const { DateTime } = luxon;

let store;
let models;

beforeEach(async () => {
    store = await setupPosEnv();
    models = store.models;
});

describe("PosStore - loyalty essentials", () => {
    test("updatePrograms adds new couponPointChanges correctly", async () => {
        const order = store.addNewOrder();

        const partner = models["res.partner"].get(1);
        const program = models["loyalty.program"].get(3);
        program.is_nominative = true;

        models["loyalty.program"].getAll = () => [program];

        order.getPartner = () => partner;
        order._programIsApplicable = () => true;
        order._code_activated_coupon_ids = [];
        order.uiState.couponPointChanges = {};
        order.pricelist_id = { id: 1 };
        order.getSelectedOrderline = () => ({
            product_id: { id: 42 },
            gift_code: "XYZ123",
        });

        order.pointsForPrograms = () => ({
            [program.id]: [{ points: 10 }],
        });

        await store.updatePrograms();

        const changes = order.uiState.couponPointChanges;
        const changeList = Object.values(changes);

        expect(changeList.length).toBe(1);
        expect(changeList[0].program_id).toBe(program.id);
        expect(changeList[0].points).toBe(10);
    });

    test("couponForProgram returns nominative coupon from fetch", async () => {
        const program = models["loyalty.program"].get(1);
        program.is_nominative = true;
        const order = store.addNewOrder();
        order.getPartner = () => models["res.partner"].get(1);

        const coupon = await store.couponForProgram(program);
        expect(coupon.program_id.id).toBe(program.id);
    });

    test("activateCode handles expired program correctly", async () => {
        models["loyalty.rule"].create({
            id: 999,
            mode: "with_code",
            code: "EXPIRED",
            program_id: models["loyalty.program"].create({
                id: 999,
                date_to: DateTime.now().minus({ days: 1 }).toISODate(),
                pricelist_ids: [],
            }),
        });
        const order = store.addNewOrder();
        order.date_order = DateTime.now().toSQL();
        const result = await store.activateCode("EXPIRED");

        expect(result).toBe(true);
    });

    test("fetchLoyaltyCard returns cached card if present", async () => {
        const partnerId = 1;
        const programId = 2;
        const existing = models["loyalty.card"].create({
            id: -999,
            program_id: models["loyalty.program"].get(programId),
            partner_id: models["res.partner"].get(partnerId),
        });

        const card = await store.fetchLoyaltyCard(programId, partnerId);

        expect(card.id).toBe(existing.id);
    });

    test("preSyncAllOrders stores coupon/reward product ID mappings by line UUID", async () => {
        const coupon = models["loyalty.card"].create({
            id: -5,
            code: "X",
            program_id: models["loyalty.program"].get(1),
            points: 0,
        });
        const rewardProduct = models["product.product"].get(1);

        const fakeOrderData = {
            lines: [
                {
                    uuid: "uuid-1",
                    coupon_id: { id: coupon.id },
                    _reward_product_id: { id: rewardProduct.id },
                },
            ],
        };

        await store.preSyncAllOrders([fakeOrderData]);

        expect(store.couponByLineUuidCache["uuid-1"]).toBe(coupon.id);
        expect(store.rewardProductByLineUuidCache["uuid-1"]).toBe(rewardProduct.id);
    });
});
