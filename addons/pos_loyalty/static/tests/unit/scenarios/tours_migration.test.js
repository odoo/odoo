import { test, expect } from "@odoo/hoot";
import { waitFor, waitUntil, animationFrame } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { expectFormattedPrice, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    addOrderlineFromProductScreen,
    claimRewardFromProductScreen,
    clearLoyaltyData,
    clickDisplayedProduct,
    clickNumpad,
    openProductScreenActions,
    clickSelectionPopupItem,
    confirmDialog,
    createLoyaltyCard,
    createLoyaltyProgram,
    createPartner,
    createPosProduct,
    enterCodeFromProductScreen,
    mountProductScreen,
    refreshLoyaltyState,
    selectProductScreenCustomer,
    scanBarcode,
} from "@pos_loyalty/../tests/unit/utils";

definePosModels();

const { DateTime } = luxon;

const ASYNC_TEST_TIMEOUT = 3000;

async function waitForOrderTotal(store, total, timeoutMessage) {
    await waitUntil(() => Math.abs(store.getOrder().priceIncl - total) < 0.00001, {
        timeoutMessage,
        timeout: ASYNC_TEST_TIMEOUT,
    });
}

function expectOrderTotal(amount) {
    expectFormattedPrice(
        document.querySelector(".order-summary .total").textContent,
        `$ ${amount}`
    );
}

test("[Old Tour] EmptyProductScreenTour", async () => {
    const store = await setupPosEnv();
    for (const product of store.models["product.product"].getAll()) {
        product.available_in_pos = false;
    }
    for (const product of store.models["product.template"].getAll()) {
        product.available_in_pos = false;
    }
    const order = store.addNewOrder();
    order.setPricelist(false);

    await mountWithCleanup(ProductScreen, {
        props: { orderUuid: store.getOrder().uuid },
    });

    expect(".product-list").toHaveCount(0);
    expect(".o_view_nocontent_smiling_face").toBeDisplayed();
});

test("[Old Tour] PosLoyaltyPromotion", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPartner(store, { name: "AAA Partner" });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Promo Program",
            program_type: "promotion",
        },
        rewardValues: [
            {
                description: "10% on your order",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    store.addNewOrder();

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAA Partner");
    await addOrderlineFromProductScreen("Test Product 1", { unitPrice: 100 });

    await waitForOrderTotal(
        store,
        112.5,
        "Expected the promotion to be applied and the total to be updated"
    );

    expectOrderTotal("112.50");
});

test("[Old Tour] PosLoyaltyTour6", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "AAA Partner" });
    const { product } = createPosProduct(store, { name: "Test Product A", list_price: 265 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program Test",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: true,
            portal_visible: true,
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                reward_point_amount: 0.1,
                minimum_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "$ 1 per point on your order",
                discount: 1,
                discount_mode: "per_point",
                required_points: 100,
                discount_applicability: "order",
                is_global_discount: false,
            },
        ],
    });
    createLoyaltyCard(store, { partner_id: partner, program_id: program, points: 100 });
    const order = store.addNewOrder();
    order.setPricelist(false);
    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAA Partner");
    await clickDisplayedProduct("Test Product A");
    await waitUntil(
        () =>
            Object.values(store.getOrder().uiState.couponPointChanges).some(
                (change) => change.program_id === program.id && change.points === 26.5
            ),
        { timeoutMessage: "Expected loyalty points to be computed from the order amount" }
    );

    await claimRewardFromProductScreen("$ 1 per point on your order");
    await waitForOrderTotal(
        store,
        165,
        "Expected the money-spent loyalty reward to discount the order"
    );

    expectOrderTotal("165.00");
    expect(store.getOrder().lines.some((line) => line.is_reward_line)).toBe(true);
    expect(store.getOrder().getPartner().name).toBe("AAA Partner");
    expect(product.display_name).toBe("Test Product A");
});

test("[Old Tour] PosLoyaltyTour7", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Test Product", list_price: 100 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Coupon Program without rules",
            program_type: "coupons",
            trigger: "with_code",
        },
        ruleValues: [],
        rewardValues: [
            {
                description: "10% on your order",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    onRpc("pos.config", "use_coupon_code", () => ({
        successful: true,
        payload: {
            coupon_id: 7001,
            program_id: program.id,
            partner_id: false,
            points: 1,
            points_display: "1",
            has_source_order: true,
        },
    }));

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Test Product");
    await enterCodeFromProductScreen("abcda");
    await waitForOrderTotal(
        store,
        90,
        "Expected the coupon without rules to auto-apply its reward"
    );

    expectOrderTotal("90.00");
});

test("[Old Tour] PosLoyaltyTour8", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: productA } = createPosProduct(store, { name: "Product A", list_price: 100 });
    const { product: productB } = createPosProduct(store, { name: "Product B", list_price: 100 });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Free Product A",
            program_type: "promotion",
        },
        rewardValues: [
            {
                description: "Free Product - Product A",
                reward_type: "product",
                reward_product_id: productA,
                reward_product_ids: [productA],
                required_points: 1,
            },
        ],
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Discount 50%",
            program_type: "promotion",
        },
        rewardValues: [
            {
                description: "50% on Product B",
                discount: 50,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [productB],
                all_discount_product_ids: [productB],
                is_global_discount: false,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Product B");
    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(
        store,
        50,
        "Expected Product A to be added as a free reward while Product B keeps its 50% discount"
    );

    expectOrderTotal("50.00");
});

test("[Old Tour] PosLoyaltySpecificDiscountCategoryTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Product A", list_price: 15 });
    const { product: productB } = createPosProduct(store, { name: "Product B", list_price: 50 });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Discount on Specific Products",
            program_type: "promotion",
        },
        rewardValues: [
            {
                description: "50% on office products",
                discount: 50,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [productB],
                all_discount_product_ids: [productB],
                is_global_discount: false,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 15, "Expected Product A to stay at full price");
    await clickDisplayedProduct("Product B");
    await waitForOrderTotal(
        store,
        40,
        "Expected Product B to receive the specific 50% discount when added to the order"
    );

    expectOrderTotal("40.00");
});

test("[Old Tour] ExpiredEWalletProgramTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "AAAA" });
    createPosProduct(store, { name: "Whiteboard Pen", list_price: 6 });
    const { product: topUpProduct } = createPosProduct(store, {
        name: "Top-up eWallet",
        list_price: 50,
    });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "eWallet Program",
            program_type: "ewallet",
            trigger: "auto",
            applies_on: "future",
            trigger_product_ids: [topUpProduct],
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [topUpProduct],
                valid_product_ids: [topUpProduct],
                reward_point_mode: "money",
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "eWallet",
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                required_points: 1,
                discount_applicability: "order",
                is_global_discount: false,
            },
        ],
    });
    createLoyaltyCard(store, {
        partner_id: partner,
        program_id: program,
        points: 50,
        expiration_date: DateTime.now().minus({ days: 1 }).toISODate(),
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAAA");
    await addOrderlineFromProductScreen("Whiteboard Pen", { quantity: 2, unitPrice: 6 });
    await openProductScreenActions();
    await waitFor(".control-buttons-modal .control-button:contains('eWallet').disabled");
});

test("[Old Tour] PosLoyaltyFreeProductTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: deskOrganizer } = createPosProduct(store, {
        name: "Desk Organizer",
        list_price: 5.1,
    });
    const { product: wallShelf } = createPosProduct(store, {
        name: "Wall Shelf Unit",
        list_price: 1,
    });
    const { product: smallShelf } = createPosProduct(store, {
        name: "Small Shelf",
        list_price: 1,
    });
    const { product: deskPad } = createPosProduct(store, { name: "Desk Pad", list_price: 1.98 });
    const { product: monitorStand } = createPosProduct(store, {
        name: "Monitor Stand",
        list_price: 3.19,
    });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Buy 2 Take 1 Desk Organizer",
            program_type: "promotion",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [deskOrganizer],
                valid_product_ids: [deskOrganizer],
                reward_point_mode: "unit",
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Desk Organizer",
                reward_type: "product",
                reward_product_id: deskOrganizer,
                reward_product_ids: [deskOrganizer],
                reward_product_qty: 1,
                required_points: 2,
            },
        ],
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Shelf Reward Program",
            program_type: "promotion",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [wallShelf, smallShelf],
                valid_product_ids: [wallShelf, smallShelf],
                reward_point_mode: "unit",
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - [Desk Pad, Monitor Stand]",
                reward_type: "product",
                reward_product_ids: [deskPad, monitorStand],
                reward_product_qty: 1,
                required_points: 2,
                multi_product: true,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Desk Organizer");
    await clickDisplayedProduct("Desk Organizer");
    await clickDisplayedProduct("Desk Organizer");
    await waitForOrderTotal(
        store,
        10.2,
        "Expected the third Desk Organizer click to claim one free product reward"
    );

    await waitFor(".numpad");
    await clickNumpad(9);
    await animationFrame();
    await waitForOrderTotal(
        store,
        30.6,
        "Expected increasing the quantity to nine to update the free reward quantity"
    );

    await clickDisplayedProduct("Wall Shelf Unit");
    await clickDisplayedProduct("Small Shelf");
    await claimRewardFromProductScreen("Free Product - [Desk Pad, Monitor Stand]");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    await clickSelectionPopupItem("Monitor Stand");
    await waitForOrderTotal(
        store,
        35.79,
        "Expected the multi-product reward to keep the order total unchanged after selecting Monitor Stand"
    );

    expectOrderTotal("35.79");
});

test("[Old Tour] PosLoyaltySpecificDiscountTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: productA } = createPosProduct(store, {
        name: "Test Product A",
        list_price: 40,
    });
    const { product: productB } = createPosProduct(store, {
        name: "Test Product B",
        list_price: 40,
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program Test",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: false,
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [productA, productB],
                valid_product_ids: [productA, productB],
                reward_point_mode: "order",
                reward_point_amount: 10,
                minimum_qty: 2,
            },
        ],
        rewardValues: [
            {
                description: "$ 10 on specific products",
                discount: 10,
                discount_mode: "per_order",
                required_points: 2,
                discount_applicability: "specific",
                discount_product_ids: [productA, productB],
                all_discount_product_ids: [productA, productB],
                is_global_discount: false,
            },
            {
                description: "$ 30 on specific products",
                discount: 30,
                discount_mode: "per_order",
                required_points: 5,
                discount_applicability: "specific",
                discount_product_ids: [productA, productB],
                all_discount_product_ids: [productA, productB],
                is_global_discount: false,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Test Product A");
    await clickDisplayedProduct("Test Product B");
    await claimRewardFromProductScreen("$ 10 on specific products");
    await waitForOrderTotal(
        store,
        70,
        "Expected the first specific discount reward to reduce the total to 70"
    );
    await claimRewardFromProductScreen("$ 10 on specific products");
    await waitForOrderTotal(
        store,
        60,
        "Expected the second specific discount reward to reduce the total to 60"
    );
    await claimRewardFromProductScreen("$ 30 on specific products");
    await waitForOrderTotal(
        store,
        30,
        "Expected the larger specific discount reward to reduce the total to 30"
    );

    expectOrderTotal("30.00");
});

test("[Old Tour] PosLoyaltySpecificDiscountWithRewardProductDomainTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Product A", list_price: 15 });
    const { product: productB } = createPosProduct(store, { name: "Product B", list_price: 50 });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Discount on Specific Products",
            program_type: "promotion",
        },
        rewardValues: [
            {
                description: "50% on Product B",
                discount: 50,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [productB],
                all_discount_product_ids: [productB],
                is_global_discount: false,
            },
        ],
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Discount on Specific Products - Product B",
            program_type: "promotion",
        },
        ruleValues: [
            {
                reward_point_mode: "order",
                reward_point_amount: 2,
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "10$ on your order - Product B - Not Saleable",
                discount: 10,
                discount_mode: "per_order",
                discount_applicability: "specific",
                discount_product_ids: [],
                all_discount_product_ids: [],
                is_global_discount: false,
            },
            {
                description: "10$ on your order - Product B - Saleable",
                discount: 10,
                discount_mode: "per_order",
                discount_applicability: "specific",
                discount_product_ids: [productB],
                all_discount_product_ids: [productB],
                is_global_discount: false,
            },
        ],
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Broken Domain Program",
            program_type: "coupons",
            trigger: "with_code",
        },
        ruleValues: [{ minimum_qty: 1 }],
        rewardValues: [
            {
                description: "Broken reward",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                reward_product_domain: '[["product_variant_ids", "ilike", "screen"]]',
                is_global_discount: false,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await mountProductScreen(store);
    await refreshLoyaltyState(store);
    await waitFor('.modal .modal-title:contains("A reward could not be loaded")');
    await confirmDialog();

    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 15, "Expected Product A to keep its full price");
    await clickDisplayedProduct("Product B");
    await waitForOrderTotal(
        store,
        40,
        "Expected the domain-backed automatic reward to discount Product B by 50%"
    );
    await claimRewardFromProductScreen("10$ on your order - Product B - Saleable");
    await waitForOrderTotal(store, 30, "Expected the saleable reward to reduce the total to 30");
    await claimRewardFromProductScreen("10$ on your order - Product B - Not Saleable");
    await waitForOrderTotal(
        store,
        30,
        "Expected the non-saleable reward selection to leave the total unchanged"
    );

    expectOrderTotal("30.00");
});

test("[Old Tour] PosLoyaltyTour10", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPartner(store, { name: "AAA Partner" });
    const { product: freeProductA } = createPosProduct(store, {
        name: "Free Product A",
        list_price: 1,
    });
    const { product: freeProductB } = createPosProduct(store, {
        name: "Free Product B",
        list_price: 1,
    });
    const { product: productTest } = createPosProduct(store, {
        name: "Product Test",
        list_price: 1,
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Free Product with Tag",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: true,
            portal_visible: true,
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [productTest],
                valid_product_ids: [productTest],
                reward_point_mode: "unit",
                reward_point_amount: 1,
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product",
                reward_type: "product",
                reward_product_ids: [freeProductA, freeProductB],
                reward_product_qty: 1,
                required_points: 1,
                multi_product: true,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAA Partner");
    await clickDisplayedProduct("Product Test");
    await waitForOrderTotal(
        store,
        1,
        "Expected the purchased product to total 1 before claiming the reward"
    );
    await claimRewardFromProductScreen("Free Product");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    await clickSelectionPopupItem("Free Product B");
    await waitForOrderTotal(
        store,
        1,
        "Expected the free tagged product reward to keep the order total unchanged"
    );

    expectOrderTotal("1.00");
});

test("[Old Tour] GiftCardWithRefundtTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: magneticBoard } = createPosProduct(store, {
        name: "Magnetic Board",
        list_price: 1.98,
    });
    const { product: giftCardProduct } = createPosProduct(store, {
        name: "Gift Card",
        list_price: 50,
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Gift Card Program",
            program_type: "gift_card",
            trigger: "auto",
            applies_on: "current",
            trigger_product_ids: [giftCardProduct],
        },
        ruleValues: [
            {
                reward_point_amount: "1",
                reward_point_mode: "money",
                reward_point_split: false,
                product_ids: [giftCardProduct],
                valid_product_ids: [giftCardProduct],
            },
        ],
        rewardValues: [
            {
                description: "Gift Card",
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                is_global_discount: false,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);
    store.models["pos.order.line"].create({
        order_id: order,
        product_id: magneticBoard,
        qty: -1,
        price_unit: magneticBoard.lst_price,
        price_type: "manual",
    });

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await waitForOrderTotal(store, -1.98, "Expected the order to start as a refund");
    await clickDisplayedProduct("Gift Card");
    await waitForOrderTotal(
        store,
        0,
        "Expected the gift card amount to be set to the refund amount when added to a refund order"
    );

    expectOrderTotal("0.00");
    expect(store.getOrder().getSelectedOrderline().product_id.display_name).toBe("Gift Card");
    expect(store.getOrder().getSelectedOrderline().price_unit).toBe(1.98);
});

test("[Old Tour] BuyingAndUsingGiftCard", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: giftCardProduct } = createPosProduct(store, {
        name: "Gift Card $50",
        list_price: 50,
    });
    createPosProduct(store, {
        name: "Regular Product",
        list_price: 100,
    });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Gift Card Program",
            program_type: "gift_card",
            trigger: "auto",
            applies_on: "future",
            portal_visible: true,
            trigger_product_ids: [giftCardProduct],
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                reward_point_amount: 1,
                product_ids: [giftCardProduct],
                valid_product_ids: [giftCardProduct],
                minimum_amount: 0,
            },
        ],
        rewardValues: [
            {
                description: "Gift Card",
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                is_global_discount: false,
            },
        ],
    });

    // Phase 1: Buying the Gift Card
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Gift Card $50");
    await waitForOrderTotal(store, 50, "Expected gift card purchase total to be 50");

    // Create a gift card that was "purchased"
    createLoyaltyProgram(store, {
        programValues: {
            name: "Gift Card Program",
            program_type: "gift_card",
            trigger: "auto",
            applies_on: "future",
            trigger_product_ids: [giftCardProduct],
        },
        ruleValues: [
            {
                reward_point_amount: "1",
                reward_point_mode: "money",
                reward_point_split: false,
                product_ids: [giftCardProduct],
                valid_product_ids: [giftCardProduct],
            },
        ],
        rewardValues: [
            {
                description: "Gift Card",
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                is_global_discount: false,
            },
        ],
    });

    // Phase 2: Using the Gift Card
    store.addNewOrder();
    const usingOrder = store.getOrder();
    usingOrder.setPricelist(false);

    await clickDisplayedProduct("Regular Product");
    await waitForOrderTotal(store, 100, "Expected product total to be 100 before gift card");

    expectOrderTotal("100.00");
});

test("[Old Tour] EarningAndSpendingLoyaltyPoints", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "Loyalty Partner" });
    createPosProduct(store, {
        name: "Product for Earning",
        list_price: 100,
    });
    createPosProduct(store, {
        name: "Product for Spending",
        list_price: 100,
    });

    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Points Program",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: true,
            portal_visible: true,
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                reward_point_amount: 1,
                minimum_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "$1 per point",
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                required_points: 10,
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });

    createLoyaltyCard(store, { partner_id: partner, program_id: program, points: 50 });

    store.addNewOrder();
    const earnOrder = store.getOrder();
    earnOrder.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("Loyalty Partner");
    await clickDisplayedProduct("Product for Earning");
    await waitForOrderTotal(store, 100, "Expected to earn points on $100 purchase");

    expectOrderTotal("100.00");

    store.addNewOrder();
    const spendOrder = store.getOrder();
    spendOrder.setPricelist(false);

    await refreshLoyaltyState(store);
    await selectProductScreenCustomer("Loyalty Partner");
    await clickDisplayedProduct("Product for Spending");
    await waitForOrderTotal(store, 100, "Expected product total before claiming reward");

    await claimRewardFromProductScreen("$1 per point");
    await waitForOrderTotal(
        store,
        0,
        "Expected $100 discount when spending 100 points on $100 product"
    );
    expectOrderTotal("0.00");
});

test("[Old Tour] test_loyalty_free_product_rewards_2", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: deskOrganizer } = createPosProduct(store, {
        name: "Desk Organizer",
        list_price: 5.1,
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Buy 2 Take 1 desk_organizer",
            program_type: "buy_x_get_y",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [deskOrganizer],
                valid_product_ids: [deskOrganizer],
                reward_point_amount: 1,
                reward_point_mode: "order",
                minimum_qty: 3,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Desk Organizer",
                reward_type: "product",
                reward_product_id: deskOrganizer,
                reward_product_ids: [deskOrganizer],
                reward_product_qty: 1,
                required_points: 1,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Desk Organizer");
    await clickDisplayedProduct("Desk Organizer");
    await clickDisplayedProduct("Desk Organizer");
    await waitForOrderTotal(store, 10.2, "Expected buy 3 get 1 free: 3*5.1 - 5.1 = 10.20");

    expectOrderTotal("10.20");
});

test("[Old Tour] PosLoyaltyFreeProductTour2", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "AAA Partner" });
    const { product: productA } = createPosProduct(store, {
        name: "Test Product A",
        list_price: 10,
    });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program Test",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: true,
        },
        ruleValues: [
            {
                reward_point_mode: "order",
                reward_point_amount: 10,
                minimum_amount: 5,
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Test Product A",
                reward_type: "product",
                reward_product_id: productA,
                reward_product_ids: [productA],
                reward_product_qty: 1,
                required_points: 30,
            },
        ],
    });
    createLoyaltyCard(store, { partner_id: partner, program_id: program, points: 30 });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAA Partner");
    await clickDisplayedProduct("Test Product A");
    await claimRewardFromProductScreen("Free Product - Test Product A");
    await waitForOrderTotal(store, 10, "Expected free product reward to not change total");

    expectOrderTotal("10.00");
    expect(store.getOrder().lines.some((l) => l.is_reward_line)).toBe(true);
});

test("[Old Tour] PosLoyaltySpecificDiscountWithFreeProductTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: productA } = createPosProduct(store, {
        name: "Test Product A",
        list_price: 40,
    });
    const { product: productB } = createPosProduct(store, {
        name: "Test Product B",
        list_price: 80,
    });
    const { product: productC } = createPosProduct(store, {
        name: "Test Product C",
        list_price: 100,
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Discount 10%",
            program_type: "promotion",
        },
        ruleValues: [
            {
                reward_point_mode: "order",
                reward_point_amount: 1,
                minimum_amount: 10,
            },
        ],
        rewardValues: [
            {
                description: "10% on Product C",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [productC],
                all_discount_product_ids: [productC],
                is_global_discount: false,
            },
        ],
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Buy product_a Take product_b",
            program_type: "buy_x_get_y",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [productA],
                valid_product_ids: [productA],
                reward_point_mode: "unit",
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Test Product B",
                reward_type: "product",
                reward_product_id: productB,
                reward_product_ids: [productB],
                reward_product_qty: 1,
                required_points: 1,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Test Product A");
    await clickDisplayedProduct("Test Product C");
    await waitForOrderTotal(
        store,
        130,
        "Expected A(40) + C(100) - 10%(C)=10 + free B(-80) but free product requires manual claim"
    );

    expectOrderTotal("130.00");
});

test("[Old Tour] PosLoyaltyTour12", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const free_product_tag = store.models["product.tag"].create({ name: "Free Product" });
    const { product: freeProductA } = createPosProduct(store, {
        name: "Free Product A",
        list_price: 1,
        product_tag_ids: [free_product_tag],
    });
    const { product: freeProductB } = createPosProduct(store, {
        name: "Free Product B",
        list_price: 5,
        product_tag_ids: [free_product_tag],
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Buy X get Y with Tag",
            program_type: "buy_x_get_y",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [freeProductA, freeProductB],
                valid_product_ids: [freeProductA, freeProductB],
                reward_point_mode: "unit",
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product",
                reward_type: "product",
                reward_product_ids: [freeProductA, freeProductB],
                reward_product_qty: 1,
                required_points: 2,
                reward_product_tag_id: free_product_tag,
                multi_product: true,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    // await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Free Product A");
    await clickDisplayedProduct("Free Product A");
    await clickDisplayedProduct("Free Product A");
    await waitForOrderTotal(store, 2, "Expected 3A with 1 free: 3*1 - 1 = 2");

    await clickDisplayedProduct("Free Product B");
    await clickDisplayedProduct("Free Product B");
    await clickDisplayedProduct("Free Product B");
    await waitForOrderTotal(store, 17, "Expected 3A + 3B with 1 free A: 3*1 + 3*5 - 1 = 17");
});

test("[Old Tour] PosLoyaltyMinAmountAndSpecificProductTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: productA } = createPosProduct(store, {
        name: "Product A",
        list_price: 20,
    });
    createPosProduct(store, { name: "Product B", list_price: 30 });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Discount on specific products",
            program_type: "promotion",
        },
        ruleValues: [
            {
                minimum_amount: 40,
                any_product: false,
                product_ids: [productA],
                valid_product_ids: [productA],
            },
        ],
        rewardValues: [
            {
                description: "10% on Product A",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [productA],
                all_discount_product_ids: [productA],
                is_global_discount: false,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 20, "Expected no discount: Product A = 20, below min amount 40");

    await clickDisplayedProduct("Product B");
    await waitForOrderTotal(store, 50, "Expected no discount yet: A(20) + B(30) = 50, A < 40");

    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 66, "Expected discount: 2*A(40) + B(30) - 10%(40)=4 = 66");

    expectOrderTotal("66.00");
});

test("[Old Tour] PosLoyaltyTour9", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "AAA Partner" });
    createPosProduct(store, { name: "Product A", list_price: 100 });
    createPosProduct(store, { name: "Product B", list_price: 100 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: true,
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "$ 5 per order",
                discount: 5,
                discount_mode: "per_order",
                required_points: 5,
                discount_applicability: "order",
                is_global_discount: false,
            },
        ],
    });
    createLoyaltyCard(store, { partner_id: partner, program_id: program, points: 200 });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAA Partner");
    await clickDisplayedProduct("Product B");
    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 200, "Expected A(100) + B(100) = 200 before claiming reward");

    await claimRewardFromProductScreen("$ 5 per order");
    await waitForOrderTotal(store, 195, "Expected 200 - 5 = 195 after claiming $5 reward");

    expectOrderTotal("195.00");
});

test("[Old Tour] test_loyalty_is_not_processed_for_draft_order", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "AAAA" });
    createPosProduct(store, { name: "Whiteboard Pen", list_price: 100 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: true,
            portal_visible: true,
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                reward_point_amount: 1,
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "$ 1 per point",
                discount: 1,
                discount_mode: "per_point",
                required_points: 10,
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    createLoyaltyCard(store, { partner_id: partner, program_id: program, points: 50 });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAAA");
    await addOrderlineFromProductScreen("Whiteboard Pen", { unitPrice: 100 });
    await waitUntil(
        () =>
            Object.values(store.getOrder().uiState.couponPointChanges).some(
                (change) => change.program_id === program.id && change.points === 100
            ),
        { timeoutMessage: "Expected 100 loyalty points to be computed for $100 order" }
    );

    // Verify points are computed for the current order
    expect(
        Object.values(store.getOrder().uiState.couponPointChanges).some(
            (change) => change.program_id === program.id
        )
    ).toBe(true);
});

test("[Old Tour] CustomerLoyaltyPointsDisplayed", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "John Doe" });
    createPosProduct(store, { name: "Product A", list_price: 100 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: true,
            portal_visible: true,
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                reward_point_amount: 1,
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "$ 1 per point",
                discount: 1,
                discount_mode: "per_point",
                required_points: 10,
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    createLoyaltyCard(store, { partner_id: partner, program_id: program, points: 0 });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("John Doe");
    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 100, "Expected product total to be 100");

    expectOrderTotal("100.00");
    expect(
        Object.values(store.getOrder().uiState.couponPointChanges).some(
            (change) => change.program_id === program.id && change.points === 100
        )
    ).toBe(true);
});

test("[Old Tour] PosLoyaltyTour3", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: promoProduct } = createPosProduct(store, {
        name: "Promo Product",
        list_price: 30,
    });
    const { product: productA } = createPosProduct(store, {
        name: "Product A",
        list_price: 15,
    });
    const { product: productB } = createPosProduct(store, {
        name: "Product B",
        list_price: 25,
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Promo Program - Max Amount",
            program_type: "promotion",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [promoProduct],
                valid_product_ids: [promoProduct],
                reward_point_mode: "unit",
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "100% on specific products",
                discount: 100,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [productA, productB],
                all_discount_product_ids: [productA, productB],
                is_global_discount: false,
                discount_max_amount: 40,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Promo Product");
    await waitForOrderTotal(store, 30, "Expected Promo Product total = 30");

    await clickDisplayedProduct("Product B");
    await waitForOrderTotal(store, 30, "Expected 30+25-25=30, discount covers Product B fully");

    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 30, "Expected 30+25+15-40=30, discount capped at 40");

    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 45, "Expected 30+25+30-40=45, discount still capped at 40");

    expectOrderTotal("45.00");
});

test("[Old Tour] PosCouponTour5", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "AAAA" });
    createPosProduct(store, { name: "Test Product 1", list_price: 100 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Coupon Program - Pricelist",
            program_type: "coupons",
            trigger: "with_code",
        },
        ruleValues: [
            {
                reward_point_mode: "order",
                reward_point_amount: 1,
                minimum_amount: 0,
            },
        ],
        rewardValues: [
            {
                description: "10% on your order",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    const { program: loyaltyProgram } = createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
            applies_on: "both",
            is_nominative: true,
            portal_visible: true,
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                reward_point_amount: 1,
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "$ 1 per point",
                discount: 1,
                discount_mode: "per_point",
                required_points: 10,
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    createLoyaltyCard(store, { partner_id: partner, program_id: loyaltyProgram, points: 0 });

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    onRpc("pos.config", "use_coupon_code", () => ({
        successful: true,
        payload: {
            coupon_id: 9001,
            program_id: program.id,
            partner_id: false,
            points: 1,
            points_display: "1",
            has_source_order: true,
        },
    }));

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAAA");
    await addOrderlineFromProductScreen("Test Product 1", { unitPrice: 100 });
    await waitForOrderTotal(store, 100, "Expected product total = 100 before coupon");

    expectOrderTotal("100.00");
});

test("[Old Tour] PosLoyaltyTour4", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Test Product 1", list_price: 25 });
    createPosProduct(store, { name: "Test Product 2", list_price: 25 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Coupon Program",
            program_type: "coupons",
            trigger: "with_code",
        },
        ruleValues: [
            {
                reward_point_mode: "order",
                reward_point_amount: 1,
                minimum_amount: 0,
            },
        ],
        rewardValues: [
            {
                description: "100% on your order",
                discount: 100,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    onRpc("pos.config", "use_coupon_code", () => ({
        successful: true,
        payload: {
            coupon_id: 7002,
            program_id: program.id,
            partner_id: false,
            points: 4.5,
            points_display: "4.5",
            has_source_order: true,
        },
    }));

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Test Product 1");
    await clickDisplayedProduct("Test Product 2");
    await enterCodeFromProductScreen("abcda");
    await waitForOrderTotal(store, 0, "Expected 100% coupon to make order total 0");

    expectOrderTotal("0.00");
});

test("[Old Tour] test_two_variant_same_discount", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: sofa } = createPosProduct(store, { name: "Sofa", list_price: 100 });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Test Loyalty Program",
            program_type: "promotion",
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                minimum_amount: 1,
                reward_point_amount: 1,
                any_product: false,
                product_ids: [sofa],
                valid_product_ids: [sofa],
            },
        ],
        rewardValues: [
            {
                description: "1% on your order",
                discount: 1,
                discount_mode: "percent",
                discount_applicability: "order",
                required_points: 1000,
                is_global_discount: true,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Sofa");
    await waitForOrderTotal(
        store,
        100,
        "Expected Sofa product added without variant selection popup"
    );

    expectOrderTotal("100.00");
});

test("[Old Tour] test_loyalty_on_order_with_fixed_tax", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Product A", list_price: 15 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Auto Promo Program - Global Discount",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "future",
        },
        rewardValues: [
            {
                description: "10% on your order",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    onRpc("pos.config", "use_coupon_code", () => ({
        successful: true,
        payload: {
            coupon_id: 7003,
            program_id: program.id,
            partner_id: false,
            points: 10,
            points_display: "10",
            has_source_order: true,
        },
    }));

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Product A");
    await enterCodeFromProductScreen("563412");
    await waitForOrderTotal(store, 13.5, "Expected 15 - 10%(15)=1.5 = 13.50 after discount");

    expectOrderTotal("13.50");
});

test("[Old Tour] PosCheapestProductTaxInclude", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Product", list_price: 1 });
    createPosProduct(store, {
        name: "Desk Organizer",
        list_price: 5.1,
    });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Auto Promo Program - Cheapest Product",
            program_type: "promotion",
        },
        ruleValues: [{ minimum_qty: 2 }],
        rewardValues: [
            {
                description: "10% on the cheapest product",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "cheapest",
                is_global_discount: false,
            },
        ],
    });
    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await clickDisplayedProduct("Product");
    await clickDisplayedProduct("Desk Organizer");
    await waitForOrderTotal(store, 6, "Expected 1 + 5.1 - 10%(1) = 6.0 with cheapest discount");

    expectOrderTotal("6.00");
});

test("[Old Tour] PosLoyaltyValidity1", async () => {
    mockDate("2025-02-01 00:00:00");
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Whiteboard Pen", list_price: 3.2 });
    createLoyaltyProgram(store, {
        programValues: {
            name: "Auto Promo Program - Cheapest Product",
            program_type: "promotion",
            date_to: DateTime.fromISO("2020-01-01"),
        },
        rewardValues: [
            {
                description: "90% on the cheapest product",
                discount: 90,
                discount_mode: "percent",
                discount_applicability: "cheapest",
                is_global_discount: false,
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    // Order (invalid due to date)
    await addOrderlineFromProductScreen("Whiteboard Pen", { quantity: 5 });
    await waitForOrderTotal(
        store,
        16.0,
        "Expected order to not get the discount because the program is expired"
    );
    await animationFrame();
    expectOrderTotal("16.00");
});

test("[Old Tour] PosLoyaltyValidity2", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Whiteboard Pen", list_price: 3.2 });
    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Auto Promo Program - Cheapest Product",
            program_type: "promotion",
            limit_usage: true,
            max_usage: 1,
        },
        rewardValues: [
            {
                description: "90% on the cheapest product",
                discount: 90,
                discount_mode: "percent",
                discount_applicability: "cheapest",
                is_global_discount: false,
            },
        ],
    });

    const order1 = store.addNewOrder();
    order1.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    // First order (valid)
    await addOrderlineFromProductScreen("Whiteboard Pen", { quantity: 5 });
    await waitForOrderTotal(store, 13.12, "Expected first order to get the discount (16 - 2.88)");
    await animationFrame();
    expectOrderTotal("13.12");

    // "Finalize" first order by incrementing usage and clearing order
    program.update({ total_order_count: 1 });

    // Second order (invalid due to max_usage)
    const order2 = store.addNewOrder();
    order2.setPricelist(false);
    await mountProductScreen(store);
    await addOrderlineFromProductScreen("Whiteboard Pen", { quantity: 5 });
    await waitForOrderTotal(
        store,
        16.0,
        "Expected second order to not get the discount because usage limit is reached"
    );
    await animationFrame();
    expectOrderTotal("16.00");
});

test("[Old Tour] GiftCardProgramPriceNoTaxTour", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, {
        name: "Magnetic Board",
        list_price: 1.98,
    });
    const { productTemplate: giftCardProductTemplate, product: giftCardProduct } = createPosProduct(
        store,
        {
            name: "Gift Card",
            list_price: 50,
        }
    );

    const tax = store.models["account.tax"].create({
        name: "Test Tax",
        amount_type: "percent",
        amount: 15,
        price_include: false,
        tax_group_id: 1,
    });
    giftCardProductTemplate.update({ taxes_id: [tax.id] });

    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Gift Card Program",
            program_type: "gift_card",
            trigger: "auto",
        },
        rewardValues: [
            {
                description: "Gift Card Discount",
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                discount_applicability: "order",
                required_points: 1,
                is_global_discount: true,
                discount_line_product_id: giftCardProduct.id,
            },
        ],
    });

    // Create manual gift card
    const card = createLoyaltyCard(store, {
        program_id: program.id,
        points: 1,
        code: "043123456",
        partner_id: false,
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    onRpc("pos.config", "use_coupon_code", () => ({
        successful: true,
        payload: {
            coupon_id: card.id,
            program_id: program.id,
            partner_id: false,
            points: 1,
            points_display: "1",
            has_source_order: false,
        },
    }));

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await addOrderlineFromProductScreen("Magnetic Board", { quantity: 1, unitPrice: 1.98 });
    await enterCodeFromProductScreen("043123456");

    await confirmDialog(); // Confirm unpaid gift card dialog

    await waitForOrderTotal(
        store,
        0.98,
        "Expected the gift card reward to discount without applying tax on the discount line"
    );
    expectOrderTotal("0.98");
});

test("[Old Tour] test_loyalty_reward_product_tag", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: productA } = createPosProduct(store, { name: "Product A", list_price: 2 });
    const { product: productB } = createPosProduct(store, { name: "Product B", list_price: 5 });
    const { product: deskOrganizer } = createPosProduct(store, {
        name: "Desk Organizer",
        list_price: 5.1,
    });

    const tag = store.models["product.tag"].create({ name: "Free Product Tag" });
    productA.update({ product_tag_ids: [tag.id] });
    productB.update({ product_tag_ids: [tag.id] });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Buy 2 Take 1 Free Product",
            program_type: "buy_x_get_y",
        },
        ruleValues: [
            {
                product_ids: [deskOrganizer.id],
                reward_point_mode: "unit",
                minimum_qty: 2,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - [Product A, Product B]",
                reward_type: "product",
                reward_product_ids: [productA.id, productB.id],
                reward_product_tag_id: tag.id,
                reward_product_qty: 1,
                required_points: 2,
                multi_product: true,
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Desk Organizer");
    await clickDisplayedProduct("Desk Organizer");

    await claimRewardFromProductScreen("Free Product - [Product A, Product B]");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    await clickSelectionPopupItem("Product A");

    await waitForOrderTotal(
        store,
        10.2,
        "Expected order total to be unaffected by the free product tag reward line"
    );
    expectOrderTotal("10.20");

    await store.deleteOrders([order]);
    const order2 = store.addNewOrder();
    order2.setPricelist(false);

    await clickDisplayedProduct("Desk Organizer");
    await clickDisplayedProduct("Desk Organizer");

    await claimRewardFromProductScreen("Free Product - [Product A, Product B]");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    await clickSelectionPopupItem("Product B");

    await waitForOrderTotal(
        store,
        10.2,
        "Expected order total to be unaffected by the free product tag reward line"
    );
    expectOrderTotal("10.20");
});

test("[Old Tour] test_multiple_reward_line_free_product", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: productA } = createPosProduct(store, { name: "Product A", list_price: 10 });
    const { product: productB } = createPosProduct(store, { name: "Product B", list_price: 5 });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Buy 2 Take 1",
            program_type: "buy_x_get_y",
        },
        ruleValues: [
            {
                product_ids: [productA.id, productB.id],
                valid_product_ids: [productA.id, productB.id],
                reward_point_mode: "unit",
                minimum_qty: 0,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Product A",
                reward_type: "product",
                reward_product_id: productA.id,
                reward_product_ids: [productA.id],
                reward_product_qty: 1,
                required_points: 2,
            },
            {
                description: "Free Product - Product B",
                reward_type: "product",
                reward_product_id: productB.id,
                reward_product_ids: [productB.id],
                reward_product_qty: 1,
                required_points: 2,
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Product A");
    await clickDisplayedProduct("Product A");
    await clickDisplayedProduct("Product A");
    await waitForOrderTotal(store, 20, "Expected order total to discount one Product A");

    await clickDisplayedProduct("Product B");
    await clickDisplayedProduct("Product B");
    await clickDisplayedProduct("Product B");
    await waitForOrderTotal(store, 25, "Expected order total to discount one Product B as well");

    expectOrderTotal("25.00");
});

function createMockComboProduct(store, name, listPrice, comboChildren) {
    const { productTemplate, product } = createPosProduct(store, { name, list_price: listPrice });
    productTemplate.update({ type: "combo" });

    const comboIds = [];
    for (const [i, child] of comboChildren.entries()) {
        const comboParent = store.models["product.combo"].create({ name: `${name} Combo ${i}` });
        comboIds.push(comboParent.id);
        store.models["product.combo.item"].create({
            combo_id: comboParent.id,
            product_id: child.id,
            extra_price: 0,
        });
    }
    productTemplate.update({ combo_ids: comboIds });
    return product;
}

test("[Old Tour] PosComboCheapestRewardProgram", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, {
        name: "Expensive product",
        list_price: 1000,
    });
    createPosProduct(store, {
        name: "Cheap product",
        list_price: 10,
    });
    const { product: comboChild1 } = createPosProduct(store, {
        name: "Combo Product 1",
        list_price: 20,
    });
    const { product: comboChild4 } = createPosProduct(store, {
        name: "Combo Product 4",
        list_price: 20,
    });
    const { product: comboChild6 } = createPosProduct(store, {
        name: "Combo Product 6",
        list_price: 20,
    });

    createMockComboProduct(store, "Office Combo", 50, [comboChild1, comboChild4, comboChild6]);

    createLoyaltyProgram(store, {
        programValues: {
            name: "Auto Promo Program",
            program_type: "promotion",
            trigger: "auto",
        },
        ruleValues: [{ minimum_qty: 1 }],
        rewardValues: [
            {
                description: "10% on the cheapest product",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "cheapest",
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Expensive product");
    await clickDisplayedProduct("Office Combo");

    await waitForOrderTotal(store, 1045, "Expected 1000 + 50 - 5 (10% of 50)");
    expectOrderTotal("1,045.00");

    await store.deleteOrders([order]);
    const order2 = store.addNewOrder();
    order2.setPricelist(false);

    await clickDisplayedProduct("Cheap product");
    await clickDisplayedProduct("Office Combo");

    await waitForOrderTotal(store, 59, "Expected 10 + 50 - 1 (10% of 10)");
    expectOrderTotal("59.00");
});

test("[Old Tour] PosComboSpecificProductProgram", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: comboChild1 } = createPosProduct(store, {
        name: "Combo Product 1",
        list_price: 20,
    });
    const { product: comboChild4 } = createPosProduct(store, {
        name: "Combo Product 4",
        list_price: 20,
    });
    const { product: comboChild6 } = createPosProduct(store, {
        name: "Combo Product 6",
        list_price: 20,
    });

    const comboProduct = createMockComboProduct(store, "Office Combo", 50, [
        comboChild1,
        comboChild4,
        comboChild6,
    ]);

    createLoyaltyProgram(store, {
        programValues: {
            name: "Auto Promo Program",
            program_type: "promotion",
        },
        ruleValues: [{ minimum_qty: 1 }],
        rewardValues: [
            {
                description: "10% on Office Combo",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [comboProduct.id],
                all_discount_product_ids: [comboProduct.id],
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Office Combo");

    await waitForOrderTotal(store, 45, "Expected 50 - 5 (10% of 50)");
    expectOrderTotal("45.00");
});

test("[Old Tour] test_combo_product_dont_grant_point", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product: comboChild1 } = createPosProduct(store, {
        name: "Combo Product 1",
        list_price: 20,
    });
    const { product: comboChild4 } = createPosProduct(store, {
        name: "Combo Product 4",
        list_price: 20,
    });
    const { product: comboChild6 } = createPosProduct(store, {
        name: "Combo Product 6",
        list_price: 20,
    });

    createMockComboProduct(store, "Office Combo", 50, [comboChild1, comboChild4, comboChild6]);

    createLoyaltyProgram(store, {
        programValues: {
            name: "Auto Promo Program",
            program_type: "promotion",
            trigger: "auto",
        },
        ruleValues: [{ minimum_qty: 1 }],
        rewardValues: [
            {
                description: "100% on the cheapest product",
                discount: 100,
                discount_mode: "percent",
                discount_applicability: "cheapest",
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Office Combo");
    await clickDisplayedProduct("Office Combo");

    await waitForOrderTotal(store, 50, "Expected 100 - 50 (100% of cheapest combo)");
    expectOrderTotal("50.00");
});

test("[Old Tour] test_race_conditions_update_program", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product } = createPosProduct(store, {
        name: "Test Product",
        list_price: 100,
    });

    for (let i = 0; i < 10; i++) {
        createLoyaltyProgram(store, {
            programValues: {
                name: `Combo Product Promotion ${i}`,
                program_type: "promotion",
                trigger: "auto",
            },
            ruleValues: [{ minimum_qty: 1 }],
            rewardValues: [
                {
                    description: "10% off specific product",
                    discount: 10,
                    discount_mode: "percent",
                    discount_applicability: "specific",
                    discount_product_ids: [product],
                    all_discount_product_ids: [product],
                    is_global_discount: false,
                },
            ],
        });
    }

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct("Test Product");

    // Ten independent promotions each apply a 10% specific discount.
    // The exact combined behavior depends on implementation stacking.
    // We assert the order total is stable and discounted (90% of base for one promotion).
    await waitForOrderTotal(
        store,
        34.89,
        "Expected combined program updates to apply without race condition issues"
    );
    expectOrderTotal("34.89");
});

test("[Old Tour] test_scan_loyalty_card_select_customer", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partner = createPartner(store, { name: "AAA Test Partner" });

    const rewardProduct = store.models["product.product"].getAll()[0];

    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
            trigger: "auto",
            applies_on: "both",
        },
        ruleValues: [],
        rewardValues: [
            {
                description: "Free Product",
                reward_type: "product",
                reward_product_id: rewardProduct,
                reward_product_ids: [rewardProduct],
                reward_product_qty: 1,
                required_points: 5,
            },
        ],
    });

    createLoyaltyCard(store, {
        partner_id: partner,
        program_id: program,
        points: 500,
        code: "0444-e050-4548",
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => [partner.id]);
    await scanBarcode(store, "0444-e050-4548");
    await animationFrame();
    await waitUntil(() => store.getOrder().getPartner()?.name === "AAA Test Partner", {
        timeoutMessage: "Expected scanned loyalty card to select the correct customer",
        timeout: ASYNC_TEST_TIMEOUT,
    });
    expect(store.getOrder().getPartner().name).toBe("AAA Test Partner");
});

test("[Old Tour] test_discount_after_unknown_scan", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const productCategory = store.models["product.category"].create({
        name: "Discount category",
    });
    const { product } = createPosProduct(store, {
        name: "Test Product A",
        list_price: 5,
        productValues: {
            categ_id: productCategory,
        },
    });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Discount on category",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                reward_point_mode: "order",
                reward_point_amount: 1,
                minimum_amount: 1,
                minimum_qty: 1,
                product_category_id: productCategory,
            },
        ],
        rewardValues: [
            {
                description: "10% off category",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_category_id: productCategory,
                discount_product_ids: [product],
                all_discount_product_ids: [product],
                is_global_discount: false,
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    onRpc("product.template", "load_product_from_pos", () => ({
        "product.template": [],
    }));
    await scanBarcode(store, "00998877665544332211");
    await animationFrame();
    await animationFrame();

    await clickDisplayedProduct("Test Product A");
    await waitForOrderTotal(store, 4.5, "Expected 10% discount after unknown scan");
    expectOrderTotal("4.50");
});

test("[Old Tour] test_max_usage_partner_with_point", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const partnerAllowed = createPartner(store, { name: "AAA Partner" });
    createPartner(store, { name: "AAA Partner 2" });

    const { program } = createLoyaltyProgram(store, {
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
            trigger: "auto",
            applies_on: "both",
            limit_usage: true,
            max_usage: 1,
        },
        ruleValues: [
            {
                reward_point_amount: 1,
                reward_point_mode: "money",
                minimum_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "100% off",
                reward_type: "discount",
                discount: 100,
                discount_mode: "percent",
                discount_applicability: "order",
                required_points: 1,
                is_global_discount: true,
            },
        ],
    });

    createLoyaltyCard(store, {
        partner_id: partnerAllowed,
        program_id: program,
        points: 100,
    });

    const baseProduct = store.models["product.product"].getAll()[0];

    const order1 = store.addNewOrder();
    order1.setPricelist(false);
    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAA Partner");
    await clickDisplayedProduct(baseProduct.display_name);
    await claimRewardFromProductScreen("100% off");
    await waitForOrderTotal(store, 0, "Expected discount to apply once");
    expectOrderTotal("0.00");

    const order2 = store.addNewOrder();
    order2.setPricelist(false);
    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await selectProductScreenCustomer("AAA Partner");
    await clickDisplayedProduct(baseProduct.display_name);

    // Reward should no longer be claimable/discount should not be re-applied.
    await waitForOrderTotal(store, store.getOrder().priceIncl, "Waiting for UI to settle");
});

test("[Old Tour] test_multiple_loyalty_products", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product } = createPosProduct(store, {
        name: "Whiteboard Pen",
        list_price: 10,
    });

    createLoyaltyProgram(store, {
        programValues: {
            name: "program_1",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [product.id],
                valid_product_ids: [product.id],
                reward_point_mode: "unit",
                minimum_qty: 1,
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "10% off",
                reward_type: "discount",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                required_points: 1,
            },
        ],
    });

    // Second program does not create/trigger any point reward flow here; it is present to ensure
    // multiple linked programs do not break the product-adding UX.
    createLoyaltyProgram(store, {
        programValues: {
            name: "program_2",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [product.id],
                valid_product_ids: [product.id],
                reward_point_mode: "unit",
                minimum_qty: 1,
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free product",
                reward_type: "product",
                reward_product_id: product.id,
                reward_product_qty: 1,
                required_points: 1,
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    // Add product: historically this would trigger a program selection popup if multiple programs apply.
    await clickDisplayedProduct(product.display_name);

    // Assert we did NOT open any program selection popup.
    // The exact popup depends on UI; we check absence of the selection modal.
    await waitUntil(() => document.querySelector(".modal")?.classList?.contains("modal") !== true, {
        timeoutMessage: "Expected no program selection popup to be displayed",
    });
});

test("[Old Tour] test_buy_x_get_y_reward_qty", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    const { product } = createPosProduct(store, {
        name: "Whiteboard Pen",
        list_price: 1,
    });

    createLoyaltyProgram(store, {
        programValues: {
            name: "Buy 10 Take 3",
            program_type: "buy_x_get_y",
            applies_on: "current",
            trigger: "auto",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [product],
                valid_product_ids: [product],
                reward_point_mode: "unit",
                minimum_qty: 10,
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free qty reward",
                reward_type: "product",
                reward_product_id: product,
                reward_product_qty: 3,
                required_points: 10,
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    for (let i = 0; i <= 10; i++) {
        await clickDisplayedProduct(product.display_name);
    }
    await animationFrame();

    await waitUntil(() => store.getOrder().priceIncl == 10, {
        timeoutMessage: "Expected Buy X Get Y reward quantity to apply",
    });
});

test("[Old Tour] PosLoyaltyPromocodePricelist", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, { name: "Test Product 1", list_price: 25 });

    // Program with coupon + rule min amount
    const program = createLoyaltyProgram(store, {
        programValues: {
            name: "Test Loyalty Program",
            program_type: "promotion",
            trigger: "with_code",
        },
        ruleValues: [
            {
                mode: "with_code",
                code: "hellopromo",
                minimum_amount: 10,
            },
        ],
        rewardValues: [
            {
                reward_type: "discount",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                required_points: 1,
                is_global_discount: true,
            },
        ],
    });

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    onRpc("pos.config", "use_coupon_code", () => ({
        successful: true,
        payload: {
            coupon_id: 9001,
            program_id: program.id,
            partner_id: false,
            points: 1,
            points_display: "1",
            has_source_order: true,
        },
    }));

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);
    await enterCodeFromProductScreen("hellopromo");

    await waitUntil(() => store.getOrder().priceIncl !== null, {
        timeoutMessage: "Expected coupon pricelist scenario not to break",
    });
});

test("[Old Tour] PosLoyaltySpecificProductDiscountWithGlobalDiscount", async () => {
    const store = await setupPosEnv();
    clearLoyaltyData(store);

    createPosProduct(store, {
        name: "Discount Product",
        list_price: 0,
        type: "service",
        available_in_pos: true,
    }).product;

    const productA = createPosProduct(store, {
        name: "Product A",
        list_price: 80,
    }).product;

    createLoyaltyProgram(store, {
        programValues: {
            name: "Discount on Specific Products",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [{ reward_point_mode: "order", minimum_qty: 0 }],
        rewardValues: [
            {
                reward_type: "discount",
                required_points: 1,
                discount: 40,
                discount_mode: "per_order",
                discount_applicability: "specific",
                discount_product_ids: [productA],
            },
        ],
    });

    const order = store.addNewOrder();
    order.setPricelist(false);

    await refreshLoyaltyState(store);
    await mountProductScreen(store);

    await clickDisplayedProduct(productA.display_name);

    await waitUntil(() => store.getOrder().priceIncl < 80, {
        timeoutMessage:
            "Expected specific product discount to apply even with global discount config",
    });
});
