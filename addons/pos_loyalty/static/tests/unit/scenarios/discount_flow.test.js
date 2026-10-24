import { test, expect } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
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

const Utils = { ...PosUiUtils, ...LoyaltyUiUtils, ...LoyaltyDataUtils };

definePosModels();

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
