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

const ASYNC_TEST_TIMEOUT = 3000;

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
