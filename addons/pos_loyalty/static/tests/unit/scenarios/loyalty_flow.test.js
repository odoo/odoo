import { test, expect } from "@odoo/hoot";
import { waitFor, animationFrame } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import {
    MockServer,
    onRpc,
    makeMockServer,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as LoyaltyUiUtils from "@pos_loyalty/../tests/unit/ui_utils";
import * as LoyaltyDataUtils from "@pos_loyalty/../tests/unit/utils";
import * as PosReceiptUtils from "@point_of_sale/../tests/unit/receipt_utils";

const Utils = { ...PosUiUtils, ...LoyaltyUiUtils, ...LoyaltyDataUtils, ...PosReceiptUtils };

definePosModels();

const { DateTime } = luxon;

const ASYNC_TEST_TIMEOUT = 3000;

test("[Old Tour] EmptyProductScreenTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    for (const id of MockServer.env["product.template"].search([])) {
        MockServer.env["product.template"].write([id], { available_in_pos: false });
    }
    const { templateId: giftCardTemplate, productId: giftCardProduct } = Utils.createPosProduct({
        name: "Gift Card",
        list_price: 50,
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Special Gift Card Program",
            program_type: "gift_card",
            trigger_product_ids: [giftCardProduct],
        },
    });

    await setupAndMountPosApp({
        use_pricelist: false,
        _pos_special_display_products_ids: [giftCardTemplate],
    });

    expect(".product-screen").toHaveCount(1);
    expect(".product-list").toHaveCount(0);
    expect(".product-screen .o_nocontent_help .o_view_nocontent_smiling_face").toBeDisplayed();
    expect(".product-screen .o_nocontent_help button:contains('Load Sample')").toHaveCount(1);
});

test("[Old Tour] PosLoyaltyPromotion", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "AAA Partner" });
    Utils.createPosProduct({ name: "Test Product 1", list_price: 100, taxes_id: [] });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Promo Program",
            program_type: "promotion",
        },
        ruleValues: [{ minimum_amount: 0, minimum_qty: 0 }],
        rewardValues: [
            {
                description: "10% on your order",
                reward_type: "discount",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
            },
        ],
    });

    const { programId: loyaltyProgram } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
        },
        ruleValues: [
            {
                minimum_amount: 1,
                minimum_qty: 1,
                reward_point_mode: "order",
                reward_point_amount: 500,
            },
        ],
        rewardValues: [
            {
                description: "$ 10 on your order",
                required_points: 500,
                reward_type: "discount",
                discount: 10,
                discount_mode: "per_order",
            },
        ],
    });
    Utils.createLoyaltyCard({ partner_id: partner, program_id: loyaltyProgram, points: 500 });

    const store = await setupAndMountPosApp({ use_pricelist: false });
    await Utils.selectCustomer("AAA Partner");
    await Utils.addOrderlineFromProductScreen("Test Product 1", { unitPrice: 100 });

    await Utils.waitForOrderTotal(store, 90, "Expected only the 10% promotion to be applied");
    Utils.expectRewardLine("10% on your order", "-10.00");
    Utils.expectNoRewardLine("$ 10 on your order");
    expect(
        store
            .getOrder()
            .getOrderlines()
            .filter((l) => l.is_reward_line)
    ).toHaveLength(1);
    Utils.expectOrderTotal("90.00");
});

test("[Old Tour] PosLoyaltyTour6", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "AAA Partner" });
    Utils.createPosProduct({
        name: "Test Product A",
        list_price: 265,
        taxes_id: [],
    });
    const { programId: program } = Utils.createLoyaltyProgram({
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
    Utils.createLoyaltyCard({ partner_id: partner, program_id: program, points: 100 });
    const store = await setupAndMountPosApp({ use_pricelist: false });
    await Utils.selectCustomer("AAA Partner");
    await Utils.clickDisplayedProduct("Test Product A");
    await waitFor('.loyalty-points-won:contains("26.5")', { timeout: ASYNC_TEST_TIMEOUT });

    await Utils.claimReward("$ 1 per point on your order");
    await Utils.waitForOrderTotal(
        store,
        165,
        "Expected the money-spent loyalty reward to discount the order"
    );
    Utils.expectOrderTotal("165.00");

    const order = store.getOrder();
    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();
    await waitFor(".feedback-screen .button.validation:not([disabled])", {
        timeout: ASYNC_TEST_TIMEOUT,
    });

    const { data } = Utils.renderReceipt(store, order);
    expect(data.extra_data.loyalties.map((entry) => entry.type)).toEqual([
        "Won:",
        "Spent:",
        "Balance:",
    ]);
    expect(data.extra_data.loyalties.map((entry) => entry.points).slice(0, 2)).toEqual([26.5, 100]);
});

test("[Old Tour] PosLoyaltyTour7", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPosProduct({ name: "Test Product", list_price: 100, taxes_id: [] });
    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Coupon Program without rules",
            program_type: "coupons",
            trigger: "with_code",
            applies_on: "current",
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
    const store = await setupAndMountPosApp({ use_pricelist: false });

    Utils.createLoyaltyCard({ code: "abcda", program_id: program, points: 1 });

    await Utils.addOrderlineFromProductScreen("Test Product", { quantity: 1 });
    await Utils.waitForOrderTotal(store, 100, "Expected the order total before any coupon");
    Utils.expectOrderTotal("100.00");

    await Utils.enterCode("abcda");
    await Utils.waitForOrderTotal(
        store,
        90,
        "Expected the coupon without rules to auto-apply its reward"
    );
    Utils.expectOrderTotal("90.00");
    Utils.expectRewardLine("10% on your order", "-10.00");
});

test("[Old Tour] PosLoyaltyTour8", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: productA } = Utils.createPosProduct({
        name: "Product A",
        list_price: 100,
        taxes_id: [1],
    });
    Utils.createPosProduct({ name: "Product B", list_price: 100, taxes_id: [] });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Free Product A",
            program_type: "promotion",
            applies_on: "current",
        },
        ruleValues: [{ reward_point_mode: "unit", minimum_qty: 0 }],
        rewardValues: [
            {
                description: "Free Product - Product A",
                reward_type: "product",
                reward_product_id: productA,
                reward_product_ids: [productA],
                reward_product_qty: 1,
                required_points: 1,
                is_global_discount: false,
            },
        ],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount 50%",
            program_type: "promotion",
            applies_on: "current",
        },
        ruleValues: [{ reward_point_mode: "order", reward_point_amount: 1 }],
        rewardValues: [
            {
                description: "50% on your order",
                reward_type: "discount",
                required_points: 1,
                discount: 50,
                discount_mode: "percent",
                discount_applicability: "order",
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Product B");
    await Utils.claimReward('Add "Free Product - Product A"');
    Utils.expectRewardLine("Free Product - Product A", "0.00", "1.00");
    await Utils.waitForOrderTotal(store, 50, "Expected the free Product A on top of the halved B");
    Utils.expectOrderTotal("50.00");

    // Buying a Product A as well: the free one is a separate line at 0, so the bought one
    // is still discounted (and paid for) like any other line.
    await Utils.clickDisplayedProduct("Product A");
    await Utils.waitForOrderTotal(
        store,
        107.5,
        "Expected the bought Product A to be halved by the global discount"
    );
    Utils.expectOrderTotal("107.50");
    Utils.expectRewardLine("Free Product - Product A", "0.00", "2.00");
});

test("[Old Tour] PosLoyaltySpecificDiscountCategoryTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const baseCategory = 1;
    const officeCategory = MockServer.env["product.category"].create({
        name: "Office furnitures",
        parent_id: baseCategory,
    });

    Utils.createPosProduct({
        name: "Product A",
        list_price: 15,
        taxes_id: [],
        categ_id: baseCategory,
    });
    const { productId: productB } = Utils.createPosProduct({
        name: "Product B",
        list_price: 50,
        taxes_id: [],
        categ_id: officeCategory,
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount on Specific Products",
            program_type: "promotion",
            applies_on: "current",
        },
        ruleValues: [{ reward_point_mode: "order", minimum_qty: 1 }],
        rewardValues: [
            {
                description: "50% on office products",
                reward_type: "discount",
                required_points: 1,
                discount: 50,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_category_id: officeCategory,
                all_discount_product_ids: [productB],
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Product A");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Product A",
            quantity: "1",
            price: "15.00",
        })
    ).toBe(true);
    await Utils.waitForOrderTotal(store, 15, "Expected Product A to stay at full price");
    Utils.expectOrderTotal("15.00");

    await Utils.clickDisplayedProduct("Product B");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Product B",
            quantity: "1",
            price: "50.00",
        })
    ).toBe(true);
    await Utils.waitForOrderTotal(
        store,
        40,
        "Expected Product B to receive the specific 50% discount when added to the order"
    );
    Utils.expectOrderTotal("40.00");
    Utils.expectRewardLine("50% on office products", "-25.00");
});

test("[Old Tour] ExpiredEWalletProgramTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "AAAA" });
    Utils.createPosProduct({ name: "Whiteboard Pen", list_price: 6 });
    const { productId: topUpProduct } = Utils.createPosProduct({
        name: "Top-up eWallet",
        list_price: 50,
    });
    const { programId: program } = Utils.createLoyaltyProgram({
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
    Utils.createLoyaltyCard({
        partner_id: partner,
        program_id: program,
        points: 50,
        expiration_date: DateTime.now().minus({ days: 1 }).toISODate(),
    });

    await setupAndMountPosApp({ use_pricelist: false });
    await Utils.selectCustomer("AAAA");
    await Utils.addOrderlineFromProductScreen("Whiteboard Pen", { quantity: 2, unitPrice: 6 });
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Whiteboard Pen",
            quantity: "2",
            priceUnit: "6",
            price: "12.00",
        })
    ).toBe(true);

    // The expired card leaves the program without a spendable balance, so the button
    // renders in its inert state instead of the "eWallet Pay" one.
    await Utils.openControlButtons();
    const ewalletButton = await Utils.getControlButton("eWallet");
    expect(ewalletButton.classList.contains("disabled")).toBe(true);
    expect(ewalletButton.classList.contains("highlight")).toBe(false);
});

test.timeout(10000);
test("[Old Tour] PosLoyaltyFreeProductTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: deskOrganizer } = Utils.createPosProduct({
        name: "Desk Organizer",
        list_price: 5.1,
        taxes_id: [],
    });
    const { productId: magneticBoard } = Utils.createPosProduct({
        name: "Magnetic Board",
        list_price: 1.98,
        taxes_id: [],
    });
    const { productId: whiteboardPen } = Utils.createPosProduct({
        name: "Whiteboard Pen",
        list_price: 3.2,
        taxes_id: [],
    });
    const { productId: wallShelf } = Utils.createPosProduct({
        name: "Wall Shelf Unit",
        list_price: 1.98,
        taxes_id: [],
    });
    const { productId: smallShelf } = Utils.createPosProduct({
        name: "Small Shelf",
        list_price: 2.83,
        taxes_id: [],
    });
    const { productId: deskPad } = Utils.createPosProduct({
        name: "Desk Pad",
        list_price: 1.98,
        taxes_id: [],
    });
    const { productId: monitorStand } = Utils.createPosProduct({
        name: "Monitor Stand",
        list_price: 3.19,
        taxes_id: [],
    });

    const rewardProductTag = MockServer.env["product.tag"].create({
        name: "reward_product_tag",
        product_product_ids: [deskPad, monitorStand],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy 2 Take 1 desk_organizer",
            program_type: "promotion",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [deskOrganizer],
                valid_product_ids: [deskOrganizer],
                reward_point_mode: "unit",
                minimum_qty: 0,
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
                is_global_discount: false,
            },
        ],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy 3 magnetic_board, Take 1 whiteboard_pen",
            program_type: "promotion",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [magneticBoard],
                valid_product_ids: [magneticBoard],
                reward_point_mode: "unit",
                minimum_qty: 0,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Whiteboard Pen",
                reward_type: "product",
                reward_product_id: whiteboardPen,
                reward_product_ids: [whiteboardPen],
                reward_product_qty: 1,
                required_points: 3,
                is_global_discount: false,
            },
        ],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "2 items of shelves, get desk_pad/monitor_stand free",
            program_type: "promotion",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [wallShelf, smallShelf],
                valid_product_ids: [wallShelf, smallShelf],
                reward_point_mode: "unit",
                minimum_qty: 0,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - [Desk Pad, Monitor Stand]",
                reward_type: "product",
                reward_product_tag_id: rewardProductTag,
                reward_product_ids: [deskPad, monitorStand],
                reward_product_qty: 1,
                required_points: 2,
                multi_product: true,
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.addOrderlineFromProductScreen("Desk Organizer", { quantity: 2 });
    await Utils.expectRewardButtonHighlighted(true);
    await Utils.claimReward('Add "Free Product - Desk Organizer"');
    Utils.expectRewardLine("Free Product - Desk Organizer", "0.00", "1");

    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.clickDisplayedProduct("Desk Organizer");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Desk Organizer",
            quantity: "4",
        })
    ).toBe(true);
    Utils.expectRewardLine("Free Product - Desk Organizer", "0.00", "2");

    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.expectRewardButtonHighlighted(false);
    await Utils.waitForOrderTotal(store, 25.5, "Expected two free Desk Organizers out of seven");
    Utils.expectOrderTotal("25.50");
    await Utils.finalizeOrder("Cash", "30");

    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.claimReward('Add "Free Product - Desk Organizer"');
    Utils.expectRewardLine("Free Product - Desk Organizer", "0.00", "1");

    await Utils.clickOrderline("Desk Organizer");
    await Utils.sendBufferKeys("9");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Desk Organizer",
            quantity: "9",
        })
    ).toBe(true);
    Utils.expectRewardLine("Free Product - Desk Organizer", "0.00", "4");

    // Removing the reward line puts the selection back on the paid line.
    await Utils.selectRewardOrderline("Free Product - Desk Organizer");
    await Utils.sendBufferKeys("Backspace");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Desk Organizer",
            quantity: "9",
        })
    ).toBe(true);
    await Utils.sendBufferKeys("Backspace");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Desk Organizer",
            quantity: "0",
        })
    ).toBe(true);
    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.expectRewardButtonHighlighted(true);
    // The reward is left unclaimed: no reward line should be synced with the order.
    await Utils.waitForOrderTotal(store, 10.2, "Expected the reward to stay unclaimed");
    Utils.expectOrderTotal("10.20");
    Utils.expectNoRewardLine("Free Product - Desk Organizer");
    await Utils.finalizeOrder("Cash", "20");

    await Utils.addOrderlineFromProductScreen("Magnetic Board", { quantity: 2 });
    await Utils.expectRewardButtonHighlighted(false);
    await Utils.clickDisplayedProduct("Magnetic Board");
    await Utils.expectRewardButtonHighlighted(true);
    await Utils.claimReward('Add "Free Product - Whiteboard Pen"');
    await Utils.expectRewardButtonHighlighted(false);
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "1");

    await Utils.clickOrderline("Magnetic Board");
    await Utils.sendBufferKeys("6");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Magnetic Board",
            quantity: "6",
        })
    ).toBe(true);
    await Utils.expectRewardButtonHighlighted(false);
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "2");
    await Utils.waitForOrderTotal(store, 11.88, "Expected both Whiteboard Pens to be free");
    Utils.expectOrderTotal("11.88");
    await Utils.finalizeOrder("Cash", "20");

    await Utils.addOrderlineFromProductScreen("Magnetic Board", { quantity: 6 });
    await Utils.claimReward('Add "Free Product - Whiteboard Pen"');
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "2");
    await Utils.expectRewardButtonHighlighted(false);

    await Utils.clickOrderline("Magnetic Board");
    await Utils.sendBufferKeys("Backspace");
    await Utils.expectRewardButtonHighlighted(false);
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Magnetic Board",
            quantity: "0",
        })
    ).toBe(true);
    await Utils.clickDisplayedProduct("Magnetic Board");
    await Utils.clickDisplayedProduct("Magnetic Board");
    await Utils.clickDisplayedProduct("Magnetic Board");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Magnetic Board",
            quantity: "3",
        })
    ).toBe(true);
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "1");
    await Utils.expectRewardButtonHighlighted(false);
    await Utils.waitForOrderTotal(store, 5.94, "Expected the single free Whiteboard Pen to remain");
    Utils.expectOrderTotal("5.94");
    await Utils.finalizeOrder("Cash", "10");

    // Promotion: 2 items of shelves, get desk_pad/monitor_stand free
    await Utils.clickDisplayedProduct("Wall Shelf Unit");
    await Utils.expectRewardButtonHighlighted(false);
    await Utils.clickDisplayedProduct("Small Shelf");
    await Utils.expectRewardButtonHighlighted(true);
    // Adding the reward product as a regular line does not claim the reward.
    await Utils.clickDisplayedProduct("Desk Pad");
    await Utils.expectRewardButtonHighlighted(true);

    await Utils.claimReward("Free Product - [Desk Pad, Monitor Stand]");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    expect('.selection-item:contains("Monitor Stand")').toHaveCount(1);
    await Utils.clickSelectionPopupItem("Desk Pad");
    expect(".modal").toHaveCount(0);
    Utils.expectRewardLine("Free Product - Desk Pad", "0.00", "1");

    // Remove the reward line: the cashier can then pick the other reward product.
    await Utils.sendBufferKeys("Backspace");
    expect(".modal").toHaveCount(0);
    await Utils.expectRewardButtonHighlighted(true);

    await Utils.claimReward("Free Product - [Desk Pad, Monitor Stand]");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    expect('.selection-item:contains("Monitor Stand")').toHaveCount(1);
    await Utils.clickSelectionPopupItem("Desk Pad");
    expect(".modal").toHaveCount(0);
    await Utils.expectRewardButtonHighlighted(false);
    Utils.expectRewardLine("Free Product - Desk Pad", "0.00", "1");

    await Utils.sendBufferKeys("Backspace");
    expect(".modal").toHaveCount(0);
    await Utils.expectRewardButtonHighlighted(true);

    await Utils.claimReward("Free Product - [Desk Pad, Monitor Stand]");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    expect('.selection-item:contains("Desk Pad")').toHaveCount(1);
    await Utils.clickSelectionPopupItem("Monitor Stand");
    expect(".modal").toHaveCount(0);
    await Utils.expectRewardButtonHighlighted(false);
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Free Product - Monitor Stand",
            quantity: "1",
            price: "0.00",
        })
    ).toBe(true);
    await Utils.waitForOrderTotal(store, 6.79, "Expected the Monitor Stand to be free");
    Utils.expectOrderTotal("6.79");
    await Utils.finalizeOrder("Cash", "10");
});

test("[Old Tour] PosLoyaltySpecificDiscountTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: productA } = Utils.createPosProduct({
        name: "Test Product A",
        list_price: 40,
        taxes_id: [],
    });
    const { productId: productB } = Utils.createPosProduct({
        name: "Test Product B",
        list_price: 40,
        taxes_id: [],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty Program Test",
            program_type: "loyalty",
            trigger: "auto",
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
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Test Product A");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Test Product A",
            quantity: "1",
            price: "40.00",
        })
    ).toBe(true);
    await Utils.clickDisplayedProduct("Test Product B");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Test Product B",
            quantity: "1",
            price: "40.00",
        })
    ).toBe(true);

    await Utils.claimReward("$ 10 on specific products");
    await Utils.waitForOrderTotal(
        store,
        70,
        "Expected the first specific discount reward to reduce the total to 70"
    );
    Utils.expectRewardLine("$ 10 on specific products", "-10.00", "1");
    Utils.expectOrderTotal("70.00");

    await Utils.claimReward("$ 30 on specific products");
    await Utils.waitForOrderTotal(
        store,
        40,
        "Expected the larger specific discount reward to reduce the total to 40"
    );
    Utils.expectRewardLine("$ 30 on specific products", "-30.00", "1");
    Utils.expectOrderTotal("40.00");
});

test("[Old Tour] PosLoyaltySpecificDiscountWithRewardProductDomainTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const baseCategory = 1;
    const officeCategory = MockServer.env["product.category"].create({
        name: "Office furnitures",
        parent_id: baseCategory,
    });
    const randomTag = MockServer.env["product.tag"].create({ name: "Random tag" });

    Utils.createPosProduct({
        name: "Product A",
        list_price: 15,
        taxes_id: [],
        categ_id: baseCategory,
    });
    const { productId: productB } = Utils.createPosProduct({
        name: "Product B",
        list_price: 50,
        taxes_id: [],
        categ_id: officeCategory,
        product_tag_ids: [randomTag],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount on Specific Products",
            program_type: "promotion",
            applies_on: "current",
        },
        ruleValues: [{ reward_point_mode: "order", minimum_qty: 1 }],
        rewardValues: [
            {
                description: "50% on Product B",
                reward_type: "discount",
                required_points: 1,
                discount: 50,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_domain:
                    '["&", ("categ_id", "ilike", "office"), ("name", "ilike", "Product B")]',
                all_discount_product_ids: [productB],
                is_global_discount: false,
            },
        ],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount on Specific Products - Product B",
            program_type: "promotion",
            applies_on: "current",
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
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "per_order",
                discount_applicability: "specific",
                // '["&", "&", ("categ_id", "not ilike", "Saleable"), ("name", "=", "Product B"),
                //   ("product_tag_ids", "not ilike", "test")]' resolves to Product B.
                reward_product_domain: `[["id", "in", [${productB}]]]`,
                all_discount_product_ids: [],
                is_global_discount: false,
            },
            {
                description: "10$ on your order - Product B - Saleable",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "per_order",
                discount_applicability: "specific",
                // '["&", "&", ("categ_id", "ilike", "Saleable"), ("name", "=", "Product B"),
                //   ("product_tag_ids", "not ilike", "test")]' resolves to no product at all.
                reward_product_domain: '[["id", "in", []]]',
                all_discount_product_ids: [],
                is_global_discount: false,
            },
        ],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "10% Discount Coupon Program - Discount on Specific Products",
            program_type: "coupons",
            trigger: "with_code",
            applies_on: "current",
        },
        ruleValues: [{ minimum_qty: 1 }],
        rewardValues: [
            {
                description: "Broken reward",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                reward_product_domain: '[["product_variant_ids", "ilike", "screen"]]',
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await waitFor('.modal .modal-title:contains("A reward could not be loaded")');
    await Utils.confirmDialog("Ok");
    expect(".modal").toHaveCount(0);

    await Utils.clickDisplayedProduct("Product A");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Product A",
            quantity: "1",
            price: "15.00",
        })
    ).toBe(true);
    await Utils.waitForOrderTotal(store, 15, "Expected Product A to keep its full price");
    Utils.expectOrderTotal("15.00");

    await Utils.clickDisplayedProduct("Product B");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Product B",
            quantity: "1",
            price: "50.00",
        })
    ).toBe(true);
    await Utils.waitForOrderTotal(
        store,
        40,
        "Expected the domain-backed automatic reward to discount Product B by 50%"
    );
    Utils.expectOrderTotal("40.00");

    // Its domain resolves to no product, so claiming it discounts nothing.
    await Utils.claimReward("10$ on your order - Product B - Saleable");
    await Utils.waitForOrderTotal(
        store,
        40,
        "Expected the reward whose domain matches no product to leave the total unchanged"
    );

    await Utils.claimReward("10$ on your order - Product B - Not Saleable");
    await Utils.waitForOrderTotal(
        store,
        30,
        "Expected the reward whose domain resolves to Product B to take 10 off"
    );
    Utils.expectOrderTotal("30.00");
});

test("[Old Tour] PosLoyaltyTour10", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPartner({ name: "AAA Partner" });

    const freeProductTag = MockServer.env["product.tag"].create({ name: "Free Product" });
    const { productId: freeProductA } = Utils.createPosProduct({
        name: "Free Product A",
        list_price: 1,
        taxes_id: [],
        product_tag_ids: [freeProductTag],
    });
    const { productId: freeProductB } = Utils.createPosProduct({
        name: "Free Product B",
        list_price: 1,
        taxes_id: [],
        product_tag_ids: [freeProductTag],
    });
    Utils.createPosProduct({ name: "Product Test", list_price: 1, taxes_id: [] });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Free Product with Tag",
            program_type: "loyalty",
            applies_on: "both",
            trigger: "auto",
            is_nominative: true,
            portal_visible: true,
        },
        ruleValues: [{ reward_point_mode: "unit", minimum_qty: 1 }],
        rewardValues: [
            {
                description: "Free Product - [Free Product A, Free Product B]",
                reward_type: "product",
                reward_product_tag_id: freeProductTag,
                reward_product_ids: [freeProductA, freeProductB],
                reward_product_qty: 1,
                required_points: 1,
                multi_product: true,
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.selectCustomer("AAA Partner");
    await Utils.checkSelectedCustomer("AAA Partner");

    await Utils.clickDisplayedProduct("Product Test");
    await Utils.waitForOrderTotal(
        store,
        1,
        "Expected the purchased product to total 1 before claiming the reward"
    );
    Utils.expectOrderTotal("1.00");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Product Test",
            quantity: "1",
        })
    ).toBe(true);
    await Utils.expectRewardButtonHighlighted(true);

    await Utils.claimReward("Free Product B");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    await Utils.clickSelectionPopupItem("Free Product B");
    await Utils.waitForOrderTotal(
        store,
        1,
        "Expected the free tagged product reward to keep the order total unchanged"
    );

    Utils.expectRewardLine("Free Product B", "0.00");
    Utils.expectOrderTotal("1.00");
    await Utils.expectRewardButtonHighlighted(false);
});

test("[Old Tour] GiftCardWithRefundtTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: magneticBoard } = Utils.createPosProduct({
        name: "Magnetic Board",
        list_price: 1.98,
    });
    const { productId: giftCardProduct } = Utils.createPosProduct({
        name: "Gift Card",
        list_price: 50,
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Gift Card Program",
            program_type: "gift_card",
            trigger: "auto",
            applies_on: "current",
            trigger_product_ids: [giftCardProduct],
        },
        ruleValues: [
            {
                reward_point_amount: 1,
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
    const store = await setupAndMountPosApp({ use_pricelist: false });
    const order = store.getOrder();
    await store.addLineToOrder(
        {
            product_tmpl_id: store.models["product.product"].get(magneticBoard).product_tmpl_id,
            qty: -1,
        },
        order
    );

    await Utils.waitForOrderTotal(store, -1.98, "Expected the order to start as a refund");
    await Utils.clickProductNamed("Gift Card");
    await Utils.waitForOrderTotal(
        store,
        0,
        "Expected the gift card amount to be set to the refund amount when added to a refund order"
    );

    Utils.expectOrderTotal("0.00");
    expect(store.getOrder().getSelectedOrderline().product_id.display_name).toBe("Gift Card");
    expect(store.getOrder().getSelectedOrderline().price_unit).toBe(1.98);
});

test("[Old Tour] BuyingAndUsingGiftCard", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: giftCardProduct } = Utils.createPosProduct({
        name: "Gift Card $50",
        list_price: 50,
    });
    Utils.createPosProduct({
        name: "Regular Product",
        list_price: 100,
    });

    Utils.createLoyaltyProgram({
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
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Gift Card $50");
    await Utils.waitForOrderTotal(store, 50, "Expected gift card purchase total to be 50");

    Utils.expectOrderTotal("50.00");
    await Utils.finalizeOrder("Cash", "50");

    // Phase 2: a fresh order for the customer spending the gift card
    await Utils.clickDisplayedProduct("Regular Product");
    await Utils.waitForOrderTotal(store, 100, "Expected product total to be 100 before gift card");

    Utils.expectOrderTotal("100.00");
});

test("[Old Tour] EarningAndSpendingLoyaltyPoints", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "Loyalty Partner" });
    Utils.createPosProduct({
        name: "Product for Earning",
        list_price: 100,
    });
    Utils.createPosProduct({
        name: "Product for Spending",
        list_price: 100,
    });

    const { programId: program } = Utils.createLoyaltyProgram({
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

    Utils.createLoyaltyCard({ partner_id: partner, program_id: program, points: 100 });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.selectCustomer("Loyalty Partner");
    await Utils.clickDisplayedProduct("Product for Earning");
    await Utils.waitForOrderTotal(store, 100, "Expected to earn points on $100 purchase");
    Utils.expectOrderTotal("100.00");
    await waitFor('.loyalty-points-won:contains("100")', { timeout: ASYNC_TEST_TIMEOUT });
    await Utils.finalizeOrder("Cash", "100");

    await Utils.selectCustomer("Loyalty Partner");
    await Utils.clickDisplayedProduct("Product for Spending");
    await Utils.waitForOrderTotal(store, 100, "Expected product total before claiming reward");

    await Utils.claimReward("$1 per point");
    await Utils.waitForOrderTotal(
        store,
        0,
        "Expected $100 discount when spending 100 points on $100 product"
    );
    Utils.expectOrderTotal("0.00");
});

test("[Old Tour] test_loyalty_free_product_rewards_2", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: deskOrganizer } = Utils.createPosProduct({
        name: "Desk Organizer",
        list_price: 5.1,
        taxes_id: [],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy 2 Take 1 desk_organizer",
            program_type: "buy_x_get_y",
            trigger: "auto",
            applies_on: "current",
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
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.claimReward('Add "Free Product - Desk Organizer"');
    await Utils.waitForOrderTotal(store, 15.3, "Expected buy 3 get 1 free on top: 3*5.1 = 15.30");

    Utils.expectRewardLine("Free Product - Desk Organizer", "0.00", "1.00");
    Utils.expectOrderTotal("15.30");
    await Utils.finalizeOrder("Cash", "15.30");
});

test("[Old Tour] PosLoyaltyFreeProductTour2", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "AAA Partner" });
    const { productId: productA } = Utils.createPosProduct({
        name: "Test Product A",
        list_price: 10,
        taxes_id: [1],
    });
    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty Program Test",
            program_type: "loyalty",
            trigger: "auto",
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
                is_global_discount: false,
            },
        ],
    });
    Utils.createLoyaltyCard({ partner_id: partner, program_id: program, points: 30 });
    await setupAndMountPosApp({ use_pricelist: false });

    await Utils.selectCustomer("AAA Partner");
    await Utils.addOrderlineFromProductScreen("Test Product A", { quantity: 1 });
    await Utils.expectRewardButtonHighlighted(true);

    await Utils.claimReward("Free Product - Test Product A");
    await waitFor('.orderline.fst-italic .product-name:contains("Free Product - Test Product A")');
    Utils.expectRewardLine("Free Product - Test Product A", "0.00", "1");
    await Utils.expectRewardButtonHighlighted(false);
});

test("[Old Tour] PosLoyaltySpecificDiscountWithFreeProductTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: productA } = Utils.createPosProduct({
        name: "Test Product A",
        list_price: 40,
        taxes_id: [],
    });
    const { productId: productB } = Utils.createPosProduct({
        name: "Test Product B",
        list_price: 80,
        taxes_id: [],
    });
    const { productId: productC } = Utils.createPosProduct({
        name: "Test Product C",
        list_price: 100,
        taxes_id: [],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount 10%",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
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
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [productC],
                all_discount_product_ids: [productC],
                is_global_discount: false,
            },
        ],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy product_a Take product_b",
            program_type: "buy_x_get_y",
            trigger: "auto",
            applies_on: "current",
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
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Test Product A");
    await Utils.clickDisplayedProduct("Test Product C");
    await Utils.waitForOrderTotal(
        store,
        130,
        "Expected A(40) + C(100) - 10% on C, with the free B reward left unclaimed"
    );
    Utils.expectOrderTotal("130.00");

    await Utils.expectRewardButtonHighlighted(true, false);
    const rewardButton = await Utils.getControlButton("Reward");
    await rewardButton.click();
    await animationFrame();

    await waitFor('.modal:not(.o_inactive_modal) .modal-title:contains("Available rewards")');
    await Utils.cancelActiveDialog();

    Utils.expectNoRewardLine("Free Product - Test Product B");
    Utils.expectOrderTotal("130.00");
});

test("[Old Tour] PosLoyaltyTour12", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const freeProductTag = MockServer.env["product.tag"].create({ name: "Free Product" });
    const { productId: freeProductA } = Utils.createPosProduct({
        name: "Free Product A",
        list_price: 1,
        taxes_id: [],
        product_tag_ids: [freeProductTag],
    });
    const { productId: freeProductB } = Utils.createPosProduct({
        name: "Free Product B",
        list_price: 5,
        taxes_id: [],
        product_tag_ids: [freeProductTag],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy X get Y with Tag",
            program_type: "buy_x_get_y",
            trigger: "auto",
            applies_on: "current",
            portal_visible: true,
        },
        ruleValues: [
            {
                any_product: false,
                product_tag_id: freeProductTag,
                valid_product_ids: [freeProductA, freeProductB],
                reward_point_mode: "unit",
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - [Free Product A, Free Product B]",
                reward_type: "product",
                reward_product_tag_id: freeProductTag,
                reward_product_ids: [freeProductA, freeProductB],
                reward_product_qty: 1,
                required_points: 2,
                multi_product: true,
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.addOrderlineFromProductScreen("Free Product A", { quantity: 2 });
    await Utils.clickDisplayedProduct("Free Product A");
    await Utils.waitForOrderTotal(store, 3, "Expected the three paid A to total 3");
    Utils.expectOrderTotal("3.00");

    await Utils.claimReward("Free Product - [Free Product A, Free Product B]");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    expect('.selection-item:contains("Free Product B")').toHaveCount(1);
    await Utils.clickSelectionPopupItem("Free Product A");
    expect(".modal").toHaveCount(0);
    Utils.expectRewardLine("Free Product - Free Product A", "0.00", "1");
    Utils.expectOrderTotal("3.00");

    await Utils.addOrderlineFromProductScreen("Free Product B", { quantity: 2 });
    await Utils.clickDisplayedProduct("Free Product B");
    await Utils.waitForOrderTotal(
        store,
        18,
        "Expected the three paid A and three paid B to total 18"
    );
    Utils.expectOrderTotal("18.00");
    Utils.expectRewardLine("Free Product - Free Product A", "0.00", "3");

    // Swap the claimed reward product: the free products become B instead of A.
    await Utils.selectRewardOrderline("Free Product - Free Product A");
    await Utils.sendBufferKeys("Backspace");
    await Utils.claimReward("Free Product - [Free Product A, Free Product B]");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    await Utils.clickSelectionPopupItem("Free Product B");
    expect(".modal").toHaveCount(0);
    Utils.expectRewardLine("Free Product - Free Product B", "0.00", "3");
    Utils.expectOrderTotal("18.00");
});

test("[Old Tour] PosLoyaltyMinAmountAndSpecificProductTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: productA } = Utils.createPosProduct({
        name: "Product A",
        list_price: 20,
        taxes_id: [],
    });
    Utils.createPosProduct({ name: "Product B", list_price: 30, taxes_id: [] });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount on specific products",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
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
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [productA],
                all_discount_product_ids: [productA],
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Product A");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Product A",
            quantity: "1",
            price: "20.00",
        })
    ).toBe(true);
    await Utils.waitForOrderTotal(
        store,
        20,
        "Expected no discount: Product A = 20, below min amount 40"
    );
    Utils.expectOrderTotal("20.00");
    Utils.expectNoRewardLine("10% on Product A");

    await Utils.clickDisplayedProduct("Product B");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Product B",
            quantity: "1",
            price: "30.00",
        })
    ).toBe(true);
    await Utils.waitForOrderTotal(
        store,
        50,
        "Expected no discount yet: A(20) + B(30) = 50, A < 40"
    );
    Utils.expectOrderTotal("50.00");
    Utils.expectNoRewardLine("10% on Product A");

    await Utils.clickDisplayedProduct("Product A");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Product A",
            quantity: "2",
            price: "40.00",
        })
    ).toBe(true);
    await Utils.waitForOrderTotal(store, 66, "Expected discount: 2*A(40) + B(30) - 10%(40)=4 = 66");
    Utils.expectOrderTotal("66.00");
    Utils.expectRewardLine("10% on Product A", "-4.00");
});

test("[Old Tour] PosLoyaltyTour9", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPartner({ name: "AAA Partner" });

    const tax10 = MockServer.env["account.tax"].create({
        name: "C01 Tax",
        amount: 10.0,
        amount_type: "percent",
        price_include: false,
        include_base_amount: false,
        is_base_affected: true,
        has_negative_factor: false,
        children_tax_ids: [],
        company_id: 250,
        sequence: 1,
        tax_group_id: 1,
        fiscal_position_ids: [],
    });

    Utils.createPosProduct({ name: "Product A", list_price: 100, taxes_id: [tax10] });
    Utils.createPosProduct({ name: "Product B", list_price: 100, taxes_id: [] });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Free Product A",
            program_type: "loyalty",
            trigger: "auto",
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
                description: "$ 5 on your order",
                reward_type: "discount",
                discount: 5,
                discount_mode: "per_order",
                required_points: 5,
                discount_applicability: "order",
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.selectCustomer("AAA Partner");
    await Utils.clickDisplayedProduct("Product B");
    await Utils.clickDisplayedProduct("Product A");
    await Utils.waitForOrderTotal(
        store,
        210,
        "Expected B(100 untaxed) + A(100 + 10% tax) = 210 before claiming the reward"
    );
    Utils.expectOrderTotal("210.00");
    await Utils.expectRewardButtonHighlighted(true);

    await Utils.claimReward("$ 5");
    await Utils.waitForOrderTotal(
        store,
        205,
        "Expected 210 - 5 = 205 after claiming the $5 reward"
    );
    Utils.expectOrderTotal("205.00");
});

test("[Old Tour] test_loyalty_is_not_processed_for_draft_order", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "AAAA" });
    Utils.createPosProduct({ name: "Whiteboard Pen", list_price: 100, taxes_id: [] });
    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty P",
            program_type: "loyalty",
            trigger: "auto",
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
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                required_points: 10,
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    Utils.createLoyaltyCard({ partner_id: partner, program_id: program, points: 50 });
    await setupAndMountPosApp({ use_pricelist: false });

    await Utils.selectCustomer("AAAA");
    await Utils.addOrderlineFromProductScreen("Whiteboard Pen", { unitPrice: 100 });
    await waitFor('.loyalty-points-won:contains("100")', { timeout: ASYNC_TEST_TIMEOUT });
    Utils.expectPointsAwarded("100");
    Utils.expectPointsTotal("150");

    await Utils.saveOrder();
    await Utils.selectFloatingOrder(0);
    await waitFor('.loyalty-points-won:contains("100")', { timeout: ASYNC_TEST_TIMEOUT });
    Utils.expectPointsAwarded("100");
    Utils.expectPointsTotal("150");
});

test("[Old Tour] CustomerLoyaltyPointsDisplayed", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "John Doe" });
    Utils.createPosProduct({ name: "product_a", list_price: 100, taxes_id: [] });
    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty P",
            program_type: "loyalty",
            trigger: "auto",
            applies_on: "both",
            is_nominative: true,
            portal_visible: true,
            portal_point_name: "Loyalty point(s)",
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
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                required_points: 10,
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    Utils.createLoyaltyCard({ partner_id: partner, program_id: program, points: 0 });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("product_a");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "product_a",
            quantity: "1",
            price: "100.00",
        })
    ).toBe(true);

    await Utils.selectCustomer("John Doe");
    await Utils.waitForOrderTotal(store, 100, "Expected product total to be 100");
    Utils.expectOrderTotal("100.00");
    await waitFor('.loyalty-points-won:contains("100")', { timeout: ASYNC_TEST_TIMEOUT });
    Utils.expectPointsAwarded("100");

    if (!Utils.isMobile()) {
        await Utils.expectPartnerPoints("John Doe", "100.00 Loyalty point(s)");
    }
    await Utils.finalizeOrder("Cash", "100.00");
});

test("[Old Tour] PosLoyaltyTour3", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const zeroRateTax = (name, taxGroupId) =>
        MockServer.env["account.tax"].create({
            name,
            amount: 0.0,
            amount_type: "percent",
            price_include: false,
            include_base_amount: false,
            is_base_affected: true,
            has_negative_factor: false,
            children_tax_ids: [],
            company_id: 250,
            sequence: 1,
            tax_group_id: taxGroupId,
            fiscal_position_ids: [],
        });
    const tax01 = zeroRateTax("C01 Tax", 1);
    const tax02 = zeroRateTax("C02 Tax", 3);

    const { productId: promoProduct } = Utils.createPosProduct({
        name: "Promo Product",
        list_price: 30,
        type: "service",
        taxes_id: [1],
    });
    const { productId: productA } = Utils.createPosProduct({
        name: "Product A",
        list_price: 15,
        taxes_id: [tax01],
    });
    const { productId: productB } = Utils.createPosProduct({
        name: "Product B",
        list_price: 25,
        taxes_id: [tax02],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Promo Program - Max Amount",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_domain: '[["product_variant_ids.name","=","Promo Product"]]',
                valid_product_ids: [promoProduct],
                reward_point_mode: "unit",
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "100% on specific products",
                reward_type: "discount",
                required_points: 1,
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
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Promo Product");
    await Utils.waitForOrderTotal(store, 34.5, "Expected Promo Product at 30 + 15% tax = 34.50");
    Utils.expectOrderTotal("34.50");

    await Utils.clickDisplayedProduct("Product B");
    Utils.expectRewardLine("100% on specific products", "25.00");

    await Utils.clickDisplayedProduct("Product A");
    Utils.expectRewardLine("100% on specific products", "15.00");
    await Utils.waitForOrderTotal(store, 34.5, "Expected 34.50 + 25 + 15 - 40 = 34.50 at the cap");
    Utils.expectOrderTotal("34.50");

    await Utils.clickDisplayedProduct("Product A");
    Utils.expectRewardLine("100% on specific products", "21.82");
    Utils.expectRewardLine("100% on specific products", "18.18");
    await Utils.waitForOrderTotal(store, 49.5, "Expected 34.50 + 25 + 30 - 40 = 49.50");
    Utils.expectOrderTotal("49.50");
});

test("[Old Tour] PosCouponTour5", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "AAAA" });
    Utils.createPosProduct({ name: "Test Product 1", list_price: 100, taxes_id: [] });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Coupon Program - Pricelist",
            program_type: "coupons",
            trigger: "with_code",
            applies_on: "current",
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
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    const { programId: loyaltyProgram } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty P",
            program_type: "loyalty",
            trigger: "auto",
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
                reward_type: "discount",
                discount: 1,
                discount_mode: "per_point",
                required_points: 10,
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    Utils.createLoyaltyCard({ partner_id: partner, program_id: loyaltyProgram, points: 0 });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.selectCustomer("AAAA");
    await Utils.addOrderlineFromProductScreen("Test Product 1", { unitPrice: 100 });
    await Utils.waitForOrderTotal(store, 100, "Expected product total = 100 before any discount");
    Utils.expectOrderTotal("100.00");

    await waitFor('.loyalty-points-won:contains("100")', { timeout: ASYNC_TEST_TIMEOUT });
    Utils.expectPointsAwarded("100");
});

test("[Old Tour] PosLoyaltyTour4", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const tax01 = MockServer.env["account.tax"].create({
        name: "C01 Tax",
        amount: 0.0,
        amount_type: "percent",
        price_include: false,
        include_base_amount: false,
        is_base_affected: true,
        has_negative_factor: false,
        children_tax_ids: [],
        company_id: 250,
        sequence: 1,
        tax_group_id: 1,
        fiscal_position_ids: [],
    });

    Utils.createPosProduct({ name: "Test Product 1", list_price: 25, taxes_id: [1] });
    Utils.createPosProduct({ name: "Test Product 2", list_price: 25, taxes_id: [tax01] });
    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Coupon Program - Pricelist",
            program_type: "coupons",
            trigger: "with_code",
            applies_on: "current",
        },
        ruleValues: [
            {
                mode: "auto",
                reward_point_mode: "order",
                reward_point_amount: 1,
                minimum_amount: 0,
            },
        ],
        rewardValues: [
            {
                description: "100% on your order",
                reward_type: "discount",
                required_points: 1,
                discount: 100,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    Utils.createLoyaltyCard({ code: "abcda", program_id: program, points: 4.5 });

    const publicPricelist = store.models["product.pricelist"].create({
        id: 30,
        name: "Public Pricelist",
        display_name: "Public Pricelist (USD)",
        item_ids: [],
    });

    const multiCurrency = store.models["product.pricelist"].create({
        id: 31,
        name: "Test multi-currency",
        display_name: "Test multi-currency (USD)",
        item_ids: [],
    });
    const halfPriceItems = ["Test Product 1", "Test Product 2"].map((name, index) =>
        store.models["product.pricelist.item"].create({
            id: 31 + index,
            pricelist_id: multiCurrency.id,
            product_id: store.models["product.product"].find((p) => p.display_name === name),
            compute_price: "percentage",
            percent_price: 50,
            base: "standard_price",
            min_quantity: 0,
        })
    );
    multiCurrency.item_ids = halfPriceItems;

    store.config.available_pricelist_ids = [
        ...store.config.available_pricelist_ids,
        publicPricelist,
        multiCurrency,
    ];
    store.config.use_pricelist = true;
    await animationFrame();

    await Utils.addOrderlineFromProductScreen("Test Product 1", { quantity: 1 });
    await Utils.addOrderlineFromProductScreen("Test Product 2", { quantity: 1 });

    await Utils.clickPriceList("Public Pricelist");
    await Utils.enterCode("abcda");
    await Utils.waitForOrderTotal(store, 0, "Expected the 100% coupon to zero the order");
    Utils.expectOrderTotal("0.00");

    await Utils.clickPriceList("Test multi-currency");
    await Utils.waitForOrderTotal(store, 0, "Expected the coupon to survive the pricelist change");
    Utils.expectOrderTotal("0.00");
});

test("[Old Tour] test_two_variant_same_discount", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const colorAttribute = MockServer.env["product.attribute"].create({
        name: "Color",
        display_type: "radio",
        create_variant: "dynamic",
        template_value_ids: [],
        attribute_line_ids: [],
    });
    const [redValue, blueValue] = ["red", "blue"].map((name) =>
        MockServer.env["product.attribute.value"].create({
            name,
            attribute_id: colorAttribute,
            sequence: 1,
        })
    );
    const [redTemplateValue, blueTemplateValue] = [redValue, blueValue].map((valueId, index) =>
        MockServer.env["product.template.attribute.value"].create({
            name: index === 0 ? "red" : "blue",
            attribute_id: colorAttribute,
            product_attribute_value_id: valueId,
            price_extra: 0,
            is_custom: false,
            excluded_value_ids: [],
        })
    );
    const attributeLine = MockServer.env["product.template.attribute.line"].create({
        attribute_id: colorAttribute,
        product_template_value_ids: [redTemplateValue, blueTemplateValue],
    });

    const { templateId: sofaTemplate, productId: redSofa } = Utils.createPosProduct({
        name: "Sofa",
        list_price: 100,
        taxes_id: [],
        attribute_line_ids: [attributeLine],
    });
    MockServer.env["product.product"].write([redSofa], {
        product_template_attribute_value_ids: [redTemplateValue],
        product_template_variant_value_ids: [redTemplateValue],
    });
    const blueSofa = MockServer.env["product.product"].create({
        product_tmpl_id: sofaTemplate,
        lst_price: 100,
        standard_price: 0,
        display_name: "Sofa",
        product_tag_ids: [],
        barcode: false,
        pos_categ_ids: [1],
        default_code: false,
        product_template_attribute_value_ids: [blueTemplateValue],
        product_template_variant_value_ids: [blueTemplateValue],
    });
    MockServer.env["product.template"].write([sofaTemplate], {
        product_variant_ids: [redSofa, blueSofa],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Test Loyalty Program",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                minimum_amount: 1,
                reward_point_amount: 1,
                any_product: false,
                product_ids: [redSofa, blueSofa],
                valid_product_ids: [redSofa, blueSofa],
            },
        ],
        rewardValues: [
            {
                description: "1% on your order",
                reward_type: "discount",
                discount: 1,
                discount_mode: "percent",
                discount_applicability: "order",
                required_points: 1000,
                is_global_discount: true,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Sofa");
    await waitFor(".modal");
    await Utils.confirmConfigurator();

    expect(".modal").toHaveCount(0);
    expect(Utils.hasOrderline({ productName: "Sofa", quantity: "1" })).toBe(true);
    await Utils.waitForOrderTotal(store, 100, "Expected the Sofa variant to be added at 100");
    Utils.expectOrderTotal("100.00");
});

test("[Old Tour] test_loyalty_on_order_with_fixed_tax", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const fixedTax = MockServer.env["account.tax"].create({
        name: "Fixed Tax",
        amount: 50.0,
        amount_type: "fixed",
        price_include: false,
        include_base_amount: false,
        is_base_affected: true,
        has_negative_factor: false,
        children_tax_ids: [],
        company_id: 250,
        sequence: 1,
        tax_group_id: 1,
        fiscal_position_ids: [],
    });

    Utils.createPosProduct({ name: "Product A", list_price: 15, taxes_id: [fixedTax] });
    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Auto Promo Program - Global Discount",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "future",
        },
        rewardValues: [
            {
                description: "10% on your order",
                reward_type: "discount",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });

    await setupAndMountPosApp({ use_pricelist: false });

    Utils.createLoyaltyCard({ code: "563412", program_id: program, points: 10 });

    await Utils.clickDisplayedProduct("Product A");
    await Utils.enterCode("563412");
    await waitFor('.orderline.fst-italic .product-name:contains("10% on your order")');
    Utils.expectRewardLine("10% on your order", "-1.50");
});

test("[Old Tour] PosCheapestProductTaxInclude", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const taxIncluded = MockServer.env["account.tax"].create({
        name: "Tax 1",
        type_tax_use: "sale",
        amount: 10,
        amount_type: "percent",
        price_include: true,
        include_base_amount: false,
        is_base_affected: true,
        has_negative_factor: false,
        children_tax_ids: [],
        company_id: 250,
        sequence: 1,
        tax_group_id: 1,
        fiscal_position_ids: [],
    });

    Utils.createPosProduct({ name: "Product", list_price: 1, taxes_id: [taxIncluded] });
    Utils.createPosProduct({ name: "Desk Organizer", list_price: 5.1, taxes_id: [] });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Auto Promo Program - Cheapest Product",
            program_type: "promotion",
            trigger: "auto",
        },
        ruleValues: [{ minimum_qty: 2 }],
        rewardValues: [
            {
                description: "10% on the cheapest product",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "cheapest",
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickProductNamed("Product");
    await Utils.addOrderlineFromProductScreen("Desk Organizer", { quantity: 1 });
    expect(Utils.hasOrderline({ productName: "10% on the cheapest product" })).toBe(true);
    await Utils.waitForOrderTotal(
        store,
        6,
        "Expected 1.00 tax-included + 5.10 - 10% of the cheapest = 6.00"
    );
    Utils.expectOrderTotal("6.00");
});

test("[Old Tour] PosLoyaltyValidity2", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    mockDate("2025-02-01 00:00:00");

    Utils.createPosProduct({ name: "Whiteboard Pen", list_price: 3.2, taxes_id: [] });
    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Auto Promo Program - Cheapest Product",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
            date_to: "2025-02-03",
            limit_usage: true,
            max_usage: 1,
        },
        rewardValues: [
            {
                description: "90% on the cheapest product",
                reward_type: "discount",
                required_points: 1,
                discount: 90,
                discount_mode: "percent",
                discount_applicability: "cheapest",
                is_global_discount: false,
            },
        ],
    });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.addOrderlineFromProductScreen("Whiteboard Pen", { quantity: 5 });
    Utils.expectRewardLine("90% on the cheapest product", "-2.88");
    await Utils.waitForOrderTotal(
        store,
        13.12,
        "Expected first order to get the discount (16 - 2.88)"
    );
    Utils.expectOrderTotal("13.12");
    await Utils.finalizeOrder("Cash", "20");

    store.models["loyalty.program"].get(program).update({ total_order_count: 1 });

    await Utils.addOrderlineFromProductScreen("Whiteboard Pen", { quantity: 5 });
    await Utils.expectRewardButtonHighlighted(false);
    await Utils.waitForOrderTotal(
        store,
        16.0,
        "Expected second order to not get the discount because usage limit is reached"
    );
    Utils.expectOrderTotal("16.00");
    Utils.expectNoRewardLine("90% on the cheapest product");
    await Utils.finalizeOrder("Cash", "16.00");
});

test("[Old Tour] GiftCardProgramPriceNoTaxTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPosProduct({ name: "Magnetic Board", list_price: 1.98, taxes_id: [] });

    const tax = MockServer.env["account.tax"].create({
        name: "Test Tax",
        type_tax_use: "sale",
        amount: 15,
        amount_type: "percent",
        price_include: false,
        include_base_amount: false,
        is_base_affected: true,
        has_negative_factor: false,
        children_tax_ids: [],
        company_id: 250,
        sequence: 1,
        tax_group_id: 1,
        fiscal_position_ids: [],
    });

    const { productId: giftCardProduct } = Utils.createPosProduct({
        name: "Gift Card",
        list_price: 50,
        taxes_id: [tax],
    });

    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "arbitrary_name",
            program_type: "gift_card",
            trigger: "auto",
            applies_on: "future",
            trigger_product_ids: [giftCardProduct],
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
                discount_line_product_id: giftCardProduct,
            },
        ],
    });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    Utils.createLoyaltyCard({
        program_id: program,
        points: 1,
        code: "043123456",
        partner_id: false,
    });

    await Utils.addOrderlineFromProductScreen("Magnetic Board", { quantity: 1, unitPrice: 1.98 });
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Magnetic Board",
            quantity: "1",
            priceUnit: "1.98",
            price: "1.98",
        })
    ).toBe(true);

    await Utils.enterCode("043123456");
    await waitFor('.modal:not(.o_inactive_modal):has(.modal-title:contains("Unpaid gift card"))');
    await Utils.confirmDialog();

    await Utils.clickOrderline("Gift Card");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Gift Card",
            quantity: "1",
            price: "-1.00",
        })
    ).toBe(true);

    await Utils.waitForOrderTotal(
        store,
        0.98,
        "Expected the gift card reward to discount without applying tax on the discount line"
    );
    Utils.expectOrderTotal("0.98");
});

test("[Old Tour] PosLoyaltyRewardProductTag", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const freeProductTag = MockServer.env["product.tag"].create({ name: "Free Product Tag" });
    const { productId: productA } = Utils.createPosProduct({
        name: "Product A",
        list_price: 2,
        taxes_id: [],
        product_tag_ids: [freeProductTag],
    });
    const { productId: productB } = Utils.createPosProduct({
        name: "Product B",
        list_price: 5,
        taxes_id: [],
        product_tag_ids: [freeProductTag],
    });
    const { productId: deskOrganizer } = Utils.createPosProduct({
        name: "Desk Organizer",
        list_price: 5.1,
        taxes_id: [],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy 2 Take 1 Free Product",
            program_type: "buy_x_get_y",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [deskOrganizer],
                valid_product_ids: [deskOrganizer],
                reward_point_mode: "unit",
                minimum_qty: 2,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - [Product A, Product B]",
                reward_type: "product",
                reward_product_tag_id: freeProductTag,
                reward_product_ids: [productA, productB],
                reward_product_qty: 1,
                required_points: 2,
                multi_product: true,
                is_global_discount: false,
            },
        ],
    });

    await setupAndMountPosApp({ use_pricelist: false });

    const claimFreeProduct = async (productName) => {
        await Utils.claimReward("Free Product - [Product A, Product B]");
        await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
        await Utils.clickSelectionPopupItem(productName);
        expect(".modal").toHaveCount(0);
    };

    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.expectRewardButtonHighlighted(true);
    await claimFreeProduct("Product A");
    Utils.expectRewardLine("Free Product - Product A", "0.00", "1");
    await Utils.expectRewardButtonHighlighted(false);

    // More points on the rule scale the claimed reward line up.
    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.clickDisplayedProduct("Desk Organizer");
    Utils.expectRewardLine("Free Product - Product A", "0.00", "2");
    await Utils.expectRewardButtonHighlighted(false);

    // Dropping the reward line lets the cashier pick the other tagged product.
    await Utils.selectRewardOrderline("Free Product - Product A");
    await Utils.sendBufferKeys("Backspace");
    Utils.expectNoRewardLine("Free Product - Product A");
    await Utils.expectRewardButtonHighlighted(true);
    await claimFreeProduct("Product B");
    Utils.expectRewardLine("Free Product - Product B", "0.00", "2");
    await Utils.expectRewardButtonHighlighted(false);

    await Utils.clickDisplayedProduct("Desk Organizer");
    await Utils.clickDisplayedProduct("Desk Organizer");
    Utils.expectRewardLine("Free Product - Product B", "0.00", "3");
    await Utils.expectRewardButtonHighlighted(false);
});

test("[Old Tour] test_multiple_reward_line_free_product", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: productA } = Utils.createPosProduct({
        name: "Product A",
        list_price: 10,
        taxes_id: [],
    });
    const { productId: productB } = Utils.createPosProduct({
        name: "Product B",
        list_price: 5,
        taxes_id: [],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy 2 Take 1",
            program_type: "buy_x_get_y",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [productA, productB],
                valid_product_ids: [productA, productB],
                reward_point_mode: "unit",
                minimum_qty: 0,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Product A",
                reward_type: "product",
                reward_product_id: productA,
                reward_product_ids: [productA],
                reward_product_qty: 1,
                required_points: 2,
                is_global_discount: false,
            },
            {
                description: "Free Product - Product B",
                reward_type: "product",
                reward_product_id: productB,
                reward_product_ids: [productB],
                reward_product_qty: 1,
                required_points: 2,
                is_global_discount: false,
            },
        ],
    });

    await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Product A");
    await Utils.clickDisplayedProduct("Product A");
    await Utils.clickDisplayedProduct("Product A");
    await Utils.claimReward('Add "Free Product - Product A"');
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Free Product - Product A",
            quantity: "1",
            price: "0.00",
        })
    ).toBe(true);

    await Utils.clickDisplayedProduct("Product B");
    await Utils.clickDisplayedProduct("Product B");
    await Utils.selectRewardOrderline("Free Product - Product A");
    await Utils.sendBufferKeys("1");
    await Utils.claimReward('Add "Free Product - Product B"');
    Utils.expectRewardLine("Free Product - Product B");

    // Product A's reward line stays pinned at 1 while Product B's follows the points left.
    await Utils.clickDisplayedProduct("Product B");
    Utils.expectRewardLine("Free Product - Product B", "0.00", "2.00");
    Utils.expectRewardLine("Free Product - Product A", "0.00", "1.00");

    await Utils.clickDisplayedProduct("Product B");
    await Utils.clickDisplayedProduct("Product B");
    Utils.expectRewardLine("Free Product - Product B", "0.00", "3.00");
    Utils.expectRewardLine("Free Product - Product A", "0.00", "1.00");

    await Utils.clickDisplayedProduct("Product A");
    await Utils.selectRewardOrderline("Free Product - Product A");
    await Utils.sendBufferKeys("2");
    Utils.expectRewardLine("Free Product - Product B", "0.00", "2.00");
    Utils.expectRewardLine("Free Product - Product A", "0.00", "2.00");
});

function createPercentTax(name, amount, taxGroupId, extra = {}) {
    return MockServer.env["account.tax"].create({
        name,
        type_tax_use: "sale",
        amount,
        amount_type: "percent",
        price_include: false,
        include_base_amount: false,
        is_base_affected: true,
        has_negative_factor: false,
        children_tax_ids: [],
        company_id: 250,
        sequence: 1,
        tax_group_id: taxGroupId,
        fiscal_position_ids: [],
        ...extra,
    });
}

function createOfficeComboFixture(listPrice) {
    const tax10 = createPercentTax("10%", 10, 1);
    const tax20in = createPercentTax("20% incl", 20, 3, {
        price_include: true,
        include_base_amount: true,
    });
    const tax30 = createPercentTax("30%", 30, 5);

    const child = (name, price, taxId) =>
        Utils.createPosProduct({ name, list_price: price, taxes_id: [taxId] }).productId;

    const products = {
        1: child("Combo Product 1", 10, tax10),
        2: child("Combo Product 2", 11, tax20in),
        3: child("Combo Product 3", 16, tax30),
        4: child("Combo Product 4", 20, tax10),
        5: child("Combo Product 5", 25, tax20in),
        6: child("Combo Product 6", 30, tax30),
        7: child("Combo Product 7", 32, tax10),
        8: child("Combo Product 8", 40, tax20in),
        9: child("Combo Product 9", 50, tax20in),
    };

    const makeCombo = (name, items, sequence) => {
        const itemIds = items.map(([productId, , extraPrice]) =>
            MockServer.env["product.combo.item"].create({
                combo_id: false,
                product_id: productId,
                extra_price: extraPrice,
            })
        );
        const comboId = MockServer.env["product.combo"].create({
            name,
            combo_item_ids: itemIds,
            base_price: Math.min(...items.map(([, price, extraPrice]) => price + extraPrice)),
            qty_free: 1,
            qty_max: 1,
            is_upsell: false,
            sequence,
        });
        MockServer.env["product.combo.item"].write(itemIds, { combo_id: comboId });
        return comboId;
    };

    const combos = [
        makeCombo(
            "Desks Combo",
            [
                [products[4], 20, 0],
                [products[5], 25, 2],
            ],
            0
        ),
        makeCombo(
            "Chairs Combo",
            [
                [products[6], 30, 0],
                [products[7], 32, 0],
                [products[8], 40, 5],
                [products[9], 50, 0],
            ],
            1
        ),
        makeCombo(
            "Desk Accessories Combo",
            [
                [products[1], 10, 0],
                [products[2], 11, 0],
                [products[3], 16, 2],
            ],
            2
        ),
    ];

    const { templateId, productId } = Utils.createPosProduct({
        name: "Office Combo",
        list_price: listPrice,
        type: "combo",
        taxes_id: [1],
    });
    MockServer.env["product.template"].write([templateId], { combo_ids: combos });
    return productId;
}

test("[Old Tour] PosComboCheapestRewardProgram", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPosProduct({
        name: "Expensive product",
        list_price: 1000,
        taxes_id: [1],
    });
    Utils.createPosProduct({
        name: "Cheap product",
        list_price: 1,
        taxes_id: [1],
    });
    createOfficeComboFixture(50);

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Auto Promo Program - Cheapest Product",
            program_type: "promotion",
            trigger: "auto",
        },
        ruleValues: [{ minimum_qty: 2 }],
        rewardValues: [
            {
                description: "10% on the cheapest product",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "cheapest",
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Expensive product");
    await Utils.clickDisplayedProduct("Office Combo");
    await Utils.configureAndConfirmCombo(["Combo Product 1", "Combo Product 4", "Combo Product 6"]);
    expect(Utils.hasOrderline({ productName: "10% on the cheapest product" })).toBe(true);
    await Utils.waitForOrderTotal(store, 1204, "Expected the tour's first order total");
    Utils.expectOrderTotal("1,204.00");
    await Utils.finalizeOrder("Cash", "1204.00");

    await Utils.clickDisplayedProduct("Cheap product");
    await Utils.clickDisplayedProduct("Office Combo");
    await Utils.configureAndConfirmCombo(["Combo Product 1", "Combo Product 4", "Combo Product 6"]);
    expect(Utils.hasOrderline({ productName: "10% on the cheapest product" })).toBe(true);
    await Utils.waitForOrderTotal(store, 61.03, "Expected the tour's second order total");
    Utils.expectOrderTotal("61.03");
    await Utils.finalizeOrder("Cash", "61.03");
});

test("[Old Tour] PosComboSpecificProductProgram", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const comboProduct = createOfficeComboFixture(200);

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Combo Product Promotion",
            program_type: "promotion",
            trigger: "auto",
        },
        ruleValues: [
            {
                any_product: false,
                minimum_qty: 1,
                product_ids: [comboProduct],
                valid_product_ids: [comboProduct],
            },
        ],
        rewardValues: [
            {
                description: "10% on Office Combo",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_ids: [comboProduct],
                all_discount_product_ids: [comboProduct],
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Office Combo");
    await Utils.configureAndConfirmCombo(["Combo Product 1", "Combo Product 4", "Combo Product 6"]);

    expect(Utils.hasOrderline({ productName: "10% on Office Combo" })).toBe(true);
    await Utils.waitForOrderTotal(store, 216, "Expected 240 combo total less the 10% = 216.00");
    Utils.expectOrderTotal("216.00");
    await Utils.finalizeOrder("Cash", "216.00");
});

test("[Old Tour] test_combo_product_dont_grant_point", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    createOfficeComboFixture(40);

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty Program",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                reward_point_amount: 1,
                reward_point_mode: "unit",
                minimum_amount: 20,
            },
        ],
        rewardValues: [
            {
                description: "100% on the cheapest product",
                reward_type: "discount",
                required_points: 2,
                discount: 100,
                discount_mode: "percent",
                discount_applicability: "cheapest",
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Office Combo");
    await Utils.configureAndConfirmCombo(["Combo Product 1", "Combo Product 4", "Combo Product 6"]);
    await Utils.clickDisplayedProduct("Office Combo");
    await Utils.configureAndConfirmCombo(["Combo Product 1", "Combo Product 4", "Combo Product 6"]);

    expect(Utils.hasOrderline({ productName: "100% on the cheapest product" })).toBe(true);
    await Utils.waitForOrderTotal(store, 48, "Expected the tour's total after the cheapest reward");
    Utils.expectOrderTotal("48.00");
});

test("[Old Tour] test_race_conditions_update_program", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: product } = Utils.createPosProduct({
        name: "Test Product",
        list_price: 100,
        taxes_id: [],
    });

    for (let i = 0; i < 10; i++) {
        Utils.createLoyaltyProgram({
            programValues: {
                name: "Combo Product Promotion",
                program_type: "promotion",
                trigger: "auto",
            },
            ruleValues: [{ minimum_qty: 1 }],
            rewardValues: [
                {
                    description: `10% off specific product ${i}`,
                    reward_type: "discount",
                    required_points: 1,
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

    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Test Product");
    await Utils.waitForOrderTotal(store, 34.89, "Expected ten stacked 10% discounts");
    Utils.expectOrderTotal("34.89");
    expect(".orderline").toHaveCount(11);
});

test("[Old Tour] test_scan_loyalty_card_select_customer", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "AAA Test Partner" });
    const { productId: whiteboardPen } = Utils.createPosProduct({
        name: "Whiteboard Pen",
        list_price: 3.2,
        taxes_id: [],
    });

    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
            trigger: "auto",
            applies_on: "both",
            is_nominative: true,
        },
        ruleValues: [],
        rewardValues: [
            {
                description: "Free Product - Whiteboard Pen",
                reward_type: "product",
                reward_product_id: whiteboardPen,
                reward_product_ids: [whiteboardPen],
                reward_product_qty: 1,
                required_points: 5,
                is_global_discount: false,
            },
        ],
    });

    Utils.createLoyaltyCard({
        partner_id: partner,
        program_id: program,
        points: 500,
        code: "0444-e050-4548",
    });

    await setupAndMountPosApp({ use_pricelist: false });

    await Utils.scanBarcode("0444-e050-4548");
    await Utils.ensurePane("left");
    await Utils.checkSelectedCustomer("AAA Test Partner");
});

test("[Old Tour] test_discount_after_unknown_scan", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    await makeMockServer();
    Utils.clearLoyaltyData();

    const productCategory = MockServer.env["product.category"].create({
        name: "Discount category",
    });
    const { productId: product } = Utils.createPosProduct({
        name: "Test Product A",
        list_price: 5,
        taxes_id: [],
        categ_id: productCategory,
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount on category",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                reward_point_mode: "order",
                reward_point_amount: 1,
                minimum_amount: 1,
                minimum_qty: 1,
                product_category_id: productCategory,
                valid_product_ids: [product],
            },
        ],
        rewardValues: [
            {
                description: "10% on Test Product A",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                discount_product_category_id: productCategory,
                all_discount_product_ids: [product],
                is_global_discount: false,
            },
        ],
    });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    onRpc("product.template", "load_product_from_pos", () => ({
        "product.template": [],
    }));

    await Utils.addOrderlineFromProductScreen("Test Product A", { quantity: 1 });
    await Utils.scanBarcode("00998877665544332211");

    Utils.expectRewardLine("10% on Test Product A", "-0.50");
    await Utils.waitForOrderTotal(store, 4.5, "Expected the discount to survive the unknown scan");
    Utils.expectOrderTotal("4.50");
});

test("[Old Tour] test_max_usage_partner_with_point", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partnerWithPoints = Utils.createPartner({ name: "AAA Partner" });
    Utils.createPartner({ name: "AAA Partner 2" });
    Utils.createPosProduct({ name: "Desk Organizer", list_price: 5.1, taxes_id: [] });

    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Loyalty Program",
            program_type: "loyalty",
            trigger: "auto",
            applies_on: "both",
            is_nominative: true,
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
                description: "100% on your order",
                reward_type: "discount",
                discount: 100,
                discount_mode: "percent",
                discount_applicability: "order",
                required_points: 1,
                is_global_discount: true,
            },
        ],
    });

    Utils.createLoyaltyCard({
        partner_id: partnerWithPoints,
        program_id: program,
        points: 100,
    });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.addOrderlineFromProductScreen("Desk Organizer", { quantity: 3 });
    await Utils.selectCustomer("AAA Partner 2");
    await Utils.expectRewardButtonHighlighted(true);
    await Utils.claimReward("100% on your order");
    await Utils.waitForOrderTotal(store, 0, "Expected the single allowed usage to zero the order");
    Utils.expectOrderTotal("0.00");
    await Utils.finalizeOrder("Cash", "0");

    store.models["loyalty.program"].get(program).update({ total_order_count: 1 });

    await Utils.selectCustomer("AAA Partner");
    await Utils.addOrderlineFromProductScreen("Desk Organizer", { quantity: 3 });
    await Utils.expectRewardButtonHighlighted(false);
    Utils.expectNoRewardLine("100% on your order");
});

test("[Old Tour] test_multiple_loyalty_products", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: product } = Utils.createPosProduct({
        name: "Whiteboard Pen",
        list_price: 3.2,
        taxes_id: [],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "program_1",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [product],
                valid_product_ids: [product],
                reward_point_mode: "unit",
                minimum_qty: 1,
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "10% on your order",
                reward_type: "discount",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                required_points: 1,
            },
        ],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "program_2",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [product],
                valid_product_ids: [product],
                reward_point_mode: "unit",
                minimum_qty: 1,
                reward_point_amount: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Whiteboard Pen",
                reward_type: "product",
                reward_product_id: product,
                reward_product_ids: [product],
                reward_product_qty: 1,
                required_points: 1,
                is_global_discount: false,
            },
        ],
    });

    await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Whiteboard Pen");

    expect(".selection-item").toHaveCount(0);
    expect(Utils.hasOrderline({ productName: "Whiteboard Pen", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "10% on your order", quantity: "1" })).toBe(true);
});

test("[Old Tour] test_buy_x_get_y_reward_qty", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: product } = Utils.createPosProduct({
        name: "Whiteboard Pen",
        list_price: 3.2,
        taxes_id: [],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy 10 whiteboard_pen, Take 3 whiteboard_pen",
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
                description: "Free Product - Whiteboard Pen",
                reward_type: "product",
                reward_product_id: product,
                reward_product_ids: [product],
                reward_product_qty: 3,
                required_points: 10,
                is_global_discount: false,
            },
        ],
    });

    await setupAndMountPosApp({ use_pricelist: false });

    await Utils.addOrderlineFromProductScreen("Whiteboard Pen", { quantity: 10 });
    await Utils.claimReward('Add "Free Product - Whiteboard Pen"');
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "3");

    // The reward line's quantity can be set by hand, but never above what the points allow.
    await Utils.sendBufferKeys("2");
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "2");
    await Utils.sendBufferKeys("9");
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "3");
    await Utils.finalizeOrder("Cash", "32");
});

test("[Old Tour] PosLoyaltyPromocodePricelist", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPosProduct({ name: "Test Product 1", list_price: 25, taxes_id: [1] });

    Utils.createLoyaltyProgram({
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
                description: "10% on your order",
                reward_type: "discount",
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                required_points: 1,
                is_global_discount: true,
            },
        ],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Program with a pricelist not available in the POS",
            program_type: "promotion",
            trigger: "auto",
            pricelist_ids: [2],
        },
        rewardValues: [
            {
                description: "90% on the cheapest product",
                reward_type: "discount",
                discount: 90,
                discount_mode: "percent",
                discount_applicability: "cheapest",
                is_global_discount: false,
            },
        ],
    });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.addOrderlineFromProductScreen("Test Product 1", { quantity: 1 });
    await Utils.enterCode("hellopromo");

    await Utils.waitForOrderTotal(store, 25.87, "Expected 28.75 less 10%");
    Utils.expectOrderTotal("25.87");
    Utils.expectNoRewardLine("90% on the cheapest product");
});

test("[Old Tour] PosLoyaltySpecificProductDiscountWithGlobalDiscount", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPosProduct({
        name: "Discount Product",
        list_price: 0,
        type: "service",
        taxes_id: [],
    });

    const { productId: productA } = Utils.createPosProduct({
        name: "Product A",
        list_price: 80,
        taxes_id: [],
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount on Specific Products",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [{ reward_point_mode: "order", minimum_qty: 0 }],
        rewardValues: [
            {
                description: "$ 40 on Product A",
                reward_type: "discount",
                required_points: 1,
                discount: 40,
                discount_mode: "per_order",
                discount_applicability: "specific",
                discount_product_ids: [productA],
                all_discount_product_ids: [productA],
                is_global_discount: false,
            },
        ],
    });

    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.addOrderlineFromProductScreen("Product A", { quantity: 1 });
    Utils.expectRewardLine("$ 40 on Product A", "-40.00");
    await Utils.waitForOrderTotal(store, 40, "Expected 80 less the $40 specific discount");
    Utils.expectOrderTotal("40.00");
});

test("[Old Tour] PosLoyaltyChangeRewardQty", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const partner = Utils.createPartner({ name: "DDD Test Partner" });
    Utils.createPosProduct({ name: "Desk Organizer", list_price: 5.1, taxes_id: [] });
    const { productId: whiteboardPen } = Utils.createPosProduct({
        name: "Whiteboard Pen",
        list_price: 3.2,
        taxes_id: [],
    });
    const { programId: program } = Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy 4 whiteboard_pen, Take 1 whiteboard_pen",
            program_type: "loyalty",
            trigger: "auto",
            applies_on: "both",
            is_nominative: true,
        },
        ruleValues: [
            {
                any_product: false,
                product_ids: [whiteboardPen],
                valid_product_ids: [whiteboardPen],
                reward_point_mode: "unit",
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - Whiteboard Pen",
                reward_type: "product",
                reward_product_id: whiteboardPen,
                reward_product_ids: [whiteboardPen],
                reward_product_qty: 1,
                required_points: 4,
                is_global_discount: false,
            },
        ],
    });
    Utils.createLoyaltyCard({ partner_id: partner, program_id: program, points: 100 });
    await setupAndMountPosApp({ use_pricelist: false });

    await Utils.selectCustomer("DDD Test Partner");
    await Utils.addOrderlineFromProductScreen("Desk Organizer", { quantity: 1 });
    await Utils.expectRewardButtonHighlighted(true);

    // The card holds 100 points and a free pen costs 4, so the reward is claimed at its
    // maximum quantity, which the cashier can then lower by hand.
    await Utils.claimReward("Free Product - Whiteboard Pen");
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "25");

    await Utils.sendBufferKeys("1");
    Utils.expectRewardLine("Free Product - Whiteboard Pen", "0.00", "1");
});

test("[Old Tour] test_free_product_multiple_reward_products", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const promoTag = MockServer.env["product.tag"].create({ name: "Promo Item" });
    const { productId: promoItemA } = Utils.createPosProduct({
        name: "Promo Item A",
        list_price: 10,
        taxes_id: [],
        product_tag_ids: [promoTag],
    });
    const { productId: promoItemB } = Utils.createPosProduct({
        name: "Promo Item B",
        list_price: 10,
        taxes_id: [],
        product_tag_ids: [promoTag],
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Buy 2 Take 1",
            program_type: "buy_x_get_y",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                any_product: false,
                product_tag_id: promoTag,
                valid_product_ids: [promoItemA, promoItemB],
                reward_point_mode: "unit",
                minimum_qty: 1,
            },
        ],
        rewardValues: [
            {
                description: "Free Product - [Promo Item A, Promo Item B]",
                reward_type: "product",
                reward_product_tag_id: promoTag,
                reward_product_ids: [promoItemA, promoItemB],
                reward_product_qty: 1,
                required_points: 2,
                multi_product: true,
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Promo Item A");
    await Utils.clickDisplayedProduct("Promo Item B");
    await Utils.claimReward("Buy 2 Take 1");
    await waitFor('.modal .modal-title:contains("Please select a product for this reward")');
    await Utils.clickSelectionPopupItem("Promo Item A");
    expect(".modal").toHaveCount(0);
    Utils.expectRewardLine("Free Product - Promo Item A", "0.00", "1");
    await Utils.waitForOrderTotal(store, 20, "Expected the free product to cost nothing");
    Utils.expectOrderTotal("20.00");

    // 6 items in total: the second free product is earned on a product other than the
    // one the reward line was claimed on.
    await Utils.clickDisplayedProduct("Promo Item A");
    await Utils.clickDisplayedProduct("Promo Item A");
    expect(
        Utils.hasOrderline({
            withClass: ".selected",
            productName: "Promo Item A",
            quantity: "3",
        })
    ).toBe(true);
    Utils.expectRewardLine("Free Product - Promo Item A", "0.00", "2");
    await Utils.waitForOrderTotal(store, 40, "Expected a second free product to be granted");
    Utils.expectOrderTotal("40.00");
});

test("[Old Tour] PosLoyalty2DiscountsSpecificGlobal", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPartner({ name: "AAAA" });
    const discountCategory = MockServer.env["product.category"].create({
        name: "Discount category",
    });
    Utils.createPosProduct({ name: "Test Product A", list_price: 5, taxes_id: [] });
    const { productId: productB } = Utils.createPosProduct({
        name: "Test Product B",
        list_price: 5,
        taxes_id: [],
        categ_id: discountCategory,
    });

    Utils.createLoyaltyProgram({
        programValues: {
            name: "Discount 10%",
            program_type: "promotion",
            trigger: "auto",
            applies_on: "current",
        },
        ruleValues: [
            {
                reward_point_mode: "order",
                reward_point_amount: 1,
                minimum_amount: 1,
                minimum_qty: 5,
            },
        ],
        rewardValues: [
            {
                description: "10% on your order",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "order",
                is_global_discount: true,
            },
        ],
    });
    Utils.createLoyaltyProgram({
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
            },
        ],
        rewardValues: [
            {
                description: "10% on Test Product B",
                reward_type: "discount",
                required_points: 1,
                discount: 10,
                discount_mode: "percent",
                discount_applicability: "specific",
                all_discount_product_ids: [productB],
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.selectCustomer("AAAA");
    await Utils.addOrderlineFromProductScreen("Test Product A", { quantity: 5 });
    await Utils.clickDisplayedProduct("Test Product B");

    // The order-wide discount goes first, the category one then applies on what is left
    // of Test Product B: 5 - (5 / 30 * 3) = 4.50, of which 10% is 0.45.
    await Utils.waitForOrderTotal(store, 26.55, "Expected both discounts to stack");
    Utils.expectRewardLine("10% on your order", "-3.00");
    Utils.expectRewardLine("10% on Test Product B", "-0.45");
    Utils.expectOrderTotal("26.55");
});
