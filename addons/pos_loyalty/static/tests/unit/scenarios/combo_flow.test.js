import { test, expect } from "@odoo/hoot";
import { MockServer, makeMockServer } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as LoyaltyUiUtils from "@pos_loyalty/../tests/unit/ui_utils";
import * as LoyaltyDataUtils from "@pos_loyalty/../tests/unit/utils";

const Utils = { ...PosUiUtils, ...LoyaltyUiUtils, ...LoyaltyDataUtils };

definePosModels();

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
