import { test, expect } from "@odoo/hoot";
import { waitFor, animationFrame } from "@odoo/hoot-dom";
import { MockServer, makeMockServer } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as LoyaltyUiUtils from "@pos_loyalty/../tests/unit/ui_utils";
import * as LoyaltyDataUtils from "@pos_loyalty/../tests/unit/utils";

const Utils = { ...PosUiUtils, ...LoyaltyUiUtils, ...LoyaltyDataUtils };

definePosModels();

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
