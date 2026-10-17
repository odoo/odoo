import { test, expect } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { MockServer, makeMockServer, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as LoyaltyUiUtils from "@pos_loyalty/../tests/unit/ui_utils";
import * as LoyaltyDataUtils from "@pos_loyalty/../tests/unit/utils";
import * as PosReceiptUtils from "@point_of_sale/../tests/unit/receipt_utils";

const Utils = { ...PosUiUtils, ...LoyaltyUiUtils, ...LoyaltyDataUtils, ...PosReceiptUtils };

definePosModels();

const ASYNC_TEST_TIMEOUT = 3000;

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
