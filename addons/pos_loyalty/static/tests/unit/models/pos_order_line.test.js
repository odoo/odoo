import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("non-ewallet/gift_card line does not ignore loyalty points", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order
    );

    const line = order.lines[0];
    const loyaltyProgram = store.models["loyalty.program"].get(1);

    expect(line.ignoreLoyaltyPoints({ program: loyaltyProgram })).toBe(undefined);
});

test("getEWalletGiftCardProgramType: regular line returns undefined for eWallet program type", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order
    );

    const line = order.lines[0];
    expect(line.getEWalletGiftCardProgramType()).toBe(undefined);
});

test("isGiftCardOrEWalletReward: regular line is not a gift card or eWallet reward", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order
    );

    const line = order.lines[0];
    expect(line.isGiftCardOrEWalletReward()).toBe(false);
});

test("isGiftCardOrEWalletReward: reward line from non-gift-card program is not gift card reward", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1); // loyalty program
    const coupon = store.models["loyalty.card"].get(1);

    const line = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: reward,
        coupon_id: coupon,
        price_type: "manual",
    });

    expect(line.isGiftCardOrEWalletReward()).toBe(false);
});

test("getDisplayClasses: reward line has fst-italic class", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);

    const line = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: reward,
        price_type: "manual",
    });

    const classes = line.getDisplayClasses();
    expect(classes["fst-italic"]).toBe(true);
});

test("regular line does not have fst-italic class", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order
    );

    const line = order.lines[0];
    const classes = line.getDisplayClasses();
    expect(classes["fst-italic"]).toBe(undefined);
});

test("getEWalletGiftCardProgramType: returns program type when _e_wallet_program_id is set", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const program = store.models["loyalty.program"].get(6);
    await store.addLineToOrder(
        {
            product_tmpl_id: store.models["product.template"].get(5),
            qty: 1,
        },
        order,
        { eWalletGiftCardProgram: program }
    );

    const line = order.lines[0];
    expect(line.getEWalletGiftCardProgramType()).toBe(program.program_type);
});

test("sets eWalletGiftCardProgram, giftBarcode, and giftCardId", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const program = store.models["loyalty.program"].get(1);
    const card = store.models["loyalty.card"].get(1);

    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order,
        { eWalletGiftCardProgram: program, giftBarcode: "ABCXYZ", giftCardId: card }
    );

    const line = order.lines[0];
    expect(line._e_wallet_program_id?.id).toBe(program.id);
    expect(line._gift_barcode).toBe("ABCXYZ");
    expect(line._gift_card_id?.id).toBe(card.id);
});

test("ignoreLoyaltyPoints: ignores points for gift_card program if line program does not match", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order
    );

    const gcProgram = store.models["loyalty.program"].find((p) => p.program_type === "gift_card");
    const line = order.lines[0];

    expect(line.ignoreLoyaltyPoints({ program: gcProgram })).toBe(true);
});

test("ignoreLoyaltyPoints: does not ignore points for gift_card if line program matches", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const gcProgram = store.models["loyalty.program"].find((p) => p.program_type === "gift_card");
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order,
        { eWalletGiftCardProgram: gcProgram }
    );

    const line = order.lines[0];
    expect(line.ignoreLoyaltyPoints({ program: gcProgram })).toBe(undefined);
});

test("isGiftCardOrEWalletReward: returns true for reward line linked to a gift card program", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);
    const gcProgram = store.models["loyalty.program"].find((p) => p.program_type === "gift_card");

    const gcCard = store.models["loyalty.card"].create({
        id: 88,
        program_id: gcProgram,
        partner_id: null,
        points: 50,
        code: "GC001",
    });

    const line = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: reward,
        coupon_id: gcCard,
        price_type: "manual",
    });

    expect(line.isGiftCardOrEWalletReward()).toBe(true);
});

test("getGiftCardOrEWalletBalance: returns formatted balance string of the coupon", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);
    const gcProgram = store.models["loyalty.program"].find((p) => p.program_type === "gift_card");

    const gcCard = store.models["loyalty.card"].create({
        id: 88,
        program_id: gcProgram,
        partner_id: null,
        points: 15.5,
        code: "GC001",
    });

    const line = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: reward,
        coupon_id: gcCard,
        price_type: "manual",
    });

    const balanceString = line.getGiftCardOrEWalletBalance();
    expect(typeof balanceString).toBe("string");
    expect(balanceString.includes("15.5")).toBe(true);
});
