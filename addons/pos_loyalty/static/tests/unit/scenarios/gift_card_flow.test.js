import { test, expect } from "@odoo/hoot";
import { advanceTime, animationFrame, waitFor, waitUntil } from "@odoo/hoot-dom";
import { MockServer, contains, makeMockServer } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as LoyaltyUiUtils from "@pos_loyalty/../tests/unit/ui_utils";
import * as LoyaltyDataUtils from "@pos_loyalty/../tests/unit/utils";

const Utils = { ...PosUiUtils, ...LoyaltyUiUtils, ...LoyaltyDataUtils };

definePosModels();

const { DateTime } = luxon;

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
test("[Old Tour] GiftCardWithRefundTour", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPosProduct({ name: "Magnetic Board", list_price: 1.98 });
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
            is_payment_program: true,
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

    await Utils.addOrderlineFromProductScreen("Magnetic Board", { quantity: 1 });
    Utils.expectOrderTotal("1.98");
    await Utils.finalizeOrder("Cash", "20");

    // Refund the paid order, then go back to the product screen with the refund line
    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");
    await Utils.selectTicketOrder("001");
    await clickTicketOrderline("Magnetic Board");
    await clickRefundNumpad("1");
    await Utils.clickTicketAction("Refund");
    await waitFor(".payment-screen");
    await contains(".payment-screen .back-button").click();
    await waitFor(".product-screen");
    expect(store.getOrder().isRefund).toBe(true);
    expect(Utils.hasOrderline({ productName: "Magnetic Board", quantity: "-1" })).toBe(true);
    await Utils.waitForOrderTotal(store, -1.98, "Expected the order to be the refund");

    // Selling a gift card from the refund is allowed and offsets it
    await Utils.clickDisplayedProduct("Gift Card", { exact: true });
    await Utils.waitForOrderTotal(
        store,
        0,
        "Expected the gift card amount to be set to the refund amount when added to a refund order"
    );
    expect(
        Utils.hasOrderline({ withClass: ".selected", productName: "Gift Card", quantity: "1" })
    ).toBe(true);
    Utils.expectOrderTotal("0.00");
    expect(store.getOrder().getSelectedOrderline().price_unit).toBe(1.98);
    await Utils.finalizeOrder("Cash", "0");

    // The gift card sold on that order can't be refunded
    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");
    await Utils.selectTicketOrder("002");
    await clickTicketOrderline("Gift Card");
    await clickTicketOrderline("Gift Card");
    await waitFor(".o_notification");
    expect(Utils.notifications().map((notification) => notification.message)).toInclude(
        "Refunding a top up or reward product for an eWallet or gift card program is not allowed."
    );
    expect(
        Utils.hasOrderline({ withClass: ".selected", productName: "Gift Card", refundQty: "2" })
    ).toBe(false);
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

test("[Old Tour] test_gift_card_no_date", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    const { productId: giftCardProduct } = Utils.createPosProduct({
        name: "Gift Card",
        list_price: 50,
    });
    Utils.createLoyaltyProgram({
        programValues: {
            name: "Gift Card Program",
            program_type: "gift_card",
            applies_on: "future",
            trigger_product_ids: [giftCardProduct],
        },
        ruleValues: [
            {
                reward_point_mode: "money",
                reward_point_amount: 1,
                product_ids: [giftCardProduct],
                valid_product_ids: [giftCardProduct],
            },
        ],
        rewardValues: [
            {
                description: "Gift Card",
                discount: 1,
                discount_mode: "per_point",
                is_global_discount: false,
            },
        ],
    });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("Gift Card", { exact: true });
    await Utils.ensurePane("left");
    await contains('.orderline a:contains("Sell physical gift card?")').click();
    await waitFor(".modal .o_exp_date_container input");
    await contains(".modal input#code").edit("test");
    await advanceTime(500);
    await waitUntil(() => !document.querySelector(".modal .gift-card-loading"));
    await contains(".modal input#amount").edit("42");
    await contains(".modal .o_exp_date_container input").clear();
    await contains('.modal .btn-primary:contains("Add Balance")').click();
    await animationFrame();

    expect(".modal").toHaveCount(0);
    const line = store.getOrder().getSelectedOrderline();
    expect(line.gift_card_vals.code).toBe("test");
    expect(line.gift_card_vals.expiration_date).toBe(false);
    await Utils.waitForOrderTotal(store, 42, "Expected the gift card to be sold for 42");

    await Utils.finalizeOrder("Cash", "42");
    expect(".product-screen").toHaveCount(1);
});

test("[Old Tour] RefundRulesProduct", async () => {
    await makeMockServer();
    Utils.clearLoyaltyData();

    Utils.createPartner({ name: "AAAAAAA" });
    const { productId: productA } = Utils.createPosProduct({
        name: "product_a",
        list_price: 100,
        taxes_id: [],
    });
    const { productId: giftCardProduct } = Utils.createPosProduct({
        name: "Gift Card",
        list_price: 50,
    });
    const { productId: topUpProduct } = Utils.createPosProduct({
        name: "Top-up eWallet",
        list_price: 50,
    });
    Utils.createLoyaltyProgram({
        programValues: { name: "My super program", program_type: "promotion" },
        ruleValues: [
            {
                any_product: false,
                product_ids: [productA],
                valid_product_ids: [productA],
                reward_point_mode: "order",
            },
        ],
        rewardValues: [
            {
                description: "50% on your order",
                discount: 50,
                discount_mode: "percent",
                discount_applicability: "order",
            },
        ],
    });
    for (const [programType, triggerProduct] of [
        ["gift_card", giftCardProduct],
        ["ewallet", topUpProduct],
    ]) {
        Utils.createLoyaltyProgram({
            programValues: {
                name: programType,
                program_type: programType,
                applies_on: "future",
                trigger_product_ids: [triggerProduct],
            },
            ruleValues: [
                {
                    reward_point_mode: "money",
                    reward_point_amount: 1,
                    product_ids: [triggerProduct],
                    valid_product_ids: [triggerProduct],
                },
            ],
            rewardValues: [
                {
                    description: programType,
                    discount: 1,
                    discount_mode: "per_point",
                    is_global_discount: false,
                },
            ],
        });
    }
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("product_a");
    await Utils.clickDisplayedProduct("Gift Card", { exact: true });
    await Utils.clickDisplayedProduct("Top-up eWallet");
    await Utils.selectCustomer("AAAAAAA");
    await Utils.finalizeOrder("Cash", "1000");

    await Utils.clickOrders();
    await waitFor(".ticket-screen");
    await Utils.selectTicketFilter("Paid");
    await Utils.selectTicketOrder("001");
    const notAllowed =
        "Refunding a top up or reward product for an eWallet or gift card program is not allowed.";
    for (const name of ["Gift Card", "Top-up eWallet"]) {
        await Utils.closeNotifications();
        await clickTicketOrderline(name);
        await clickRefundNumpad("1");
        await waitFor(".o_notification");
        expect(Utils.notifications().map((notification) => notification.message)).toInclude(
            notAllowed,
            { message: `${name} must not be refundable` }
        );
        expect(Utils.hasOrderline({ productName: name, refundQty: "1" })).toBe(false);
    }
    await clickTicketOrderline("product_a");
    await clickRefundNumpad("1");
    expect(Utils.hasOrderline({ productName: "product_a", refundQty: "1" })).toBe(true);

    await Utils.clickTicketAction("Refund");
    await waitFor(".payment-screen");
    const refundOrder = store.getOrder();
    expect(
        refundOrder
            .getOrderlines()
            .filter((line) => !line.is_reward_line)
            .map((line) => [line.product_id.display_name, line.qty])
    ).toEqual([["product_a", -1]]);
});

async function clickRefundNumpad(key) {
    await Utils.clickTicketNumpad(key);
    // apply the numpad input now instead of after the number buffer timeout
    await Utils.sendBufferKeys();
}

async function clickTicketOrderline(name) {
    await Utils.ensureTicketPane("right");
    await contains(`.ticket-screen .orderline .product-name:contains("${name}")`).click();
    await animationFrame();
}
