import { describe, expect, test, beforeEach } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as ResUiUtils from "@pos_restaurant/../tests/unit/ui_utils";
import { deactivateAllProgramsExcept } from "@pos_loyalty/../tests/unit/utils";

import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";
import { ProductProduct } from "@point_of_sale/../tests/unit/data/product_product.data";
import { AccountTaxGroup } from "@point_of_sale/../tests/unit/data/account_tax_group.data";
import { AccountTax } from "@point_of_sale/../tests/unit/data/account_tax.data";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";
import { ResPartner } from "@point_of_sale/../tests/unit/data/res_partner.data";
import { LoyaltyProgram } from "@pos_loyalty/../tests/unit/data/loyalty_program.data";
import { LoyaltyRule } from "@pos_loyalty/../tests/unit/data/loyalty_rule.data";
import { LoyaltyCard } from "@pos_loyalty/../tests/unit/data/loyalty_card.data";

const Utils = { ...PosUiUtils, ...ResUiUtils };
const productA20 = "Product A (20%)";
const productB25 = "Product B (25%)";
const LOYALTY_PROGRAM_ID = 9101;
const GUESTS = {
    alice: { partnerId: 9101, cardId: 9101, initialPoints: 100 },
    bob: { partnerId: 9102, cardId: 9102, initialPoints: 50 },
    carol: { partnerId: 9103, cardId: 9103, initialPoints: 0 },
};

AccountTaxGroup._records.push(
    { id: 9101, name: "TAX 20%", pos_receipt_label: "Tax" },
    { id: 9102, name: "TAX 25%", pos_receipt_label: "Tax" }
);

AccountTax._records.push(
    {
        id: 9101,
        name: "20%",
        amount: 20,
        amount_type: "percent",
        price_include: false,
        tax_group_id: 9101,
    },
    {
        id: 9102,
        name: "25%",
        amount: 25,
        amount_type: "percent",
        price_include: false,
        tax_group_id: 9102,
    }
);

function addProduct({ id, name, price, taxes, type = "consu" }) {
    ProductTemplate._records.push({
        id,
        name,
        display_name: name,
        type,
        list_price: price,
        taxes_id: taxes,
        product_variant_ids: [],
        available_in_pos: true,
    });
    ProductProduct._records.push({
        id,
        product_tmpl_id: id,
        name,
        display_name: name,
        type,
        lst_price: price,
        taxes_id: taxes,
        available_in_pos: true,
    });
}

addProduct({ id: 9101, name: productA20, price: 10, taxes: [9101] });
addProduct({ id: 9102, name: productB25, price: 20, taxes: [9102] });
addProduct({ id: 9103, name: "Split Payment Product", price: 0, taxes: [], type: "service" });

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    split_payment_product_id: 9103,
}));

for (const [name, { partnerId }] of Object.entries(GUESTS)) {
    ResPartner._records.push({
        id: partnerId,
        name,
        street: false,
        street2: false,
        city: false,
        state_id: false,
        country_id: false,
        vat: false,
        lang: "en_US",
        phone: false,
        zip: false,
        email: false,
        barcode: false,
        write_date: "2025-01-01 10:00:00",
        property_product_pricelist: false,
        parent_name: false,
        address: "\n\n  \n",
        invoice_emails: "",
        fiscal_position_id: false,
    });
}

LoyaltyProgram._records.push({
    id: LOYALTY_PROGRAM_ID,
    name: "Restaurant Loyalty",
    trigger: "auto",
    applies_on: "both",
    program_type: "loyalty",
    is_payment_program: false,
    pricelist_ids: [],
    date_from: false,
    date_to: false,
    limit_usage: false,
    max_usage: 0,
    is_nominative: true,
    portal_visible: true,
    portal_point_name: "Points",
    trigger_product_ids: [],
    rule_ids: [LOYALTY_PROGRAM_ID],
    reward_ids: [],
    write_date: "2025-01-01 10:00:00",
});

LoyaltyRule._records.push({
    id: LOYALTY_PROGRAM_ID,
    program_id: LOYALTY_PROGRAM_ID,
    valid_product_ids: [],
    any_product: true,
    currency_id: 1,
    reward_point_amount: 1,
    reward_point_split: false,
    reward_point_mode: "money",
    minimum_qty: 0,
    minimum_amount: 0,
    minimum_amount_tax_mode: "incl",
    mode: "auto",
    code: false,
    write_date: "2025-01-01 10:00:00",
});

for (const [name, { partnerId, cardId, initialPoints }] of Object.entries(GUESTS)) {
    LoyaltyCard._records.push({
        id: cardId,
        code: `CARD-${name.toUpperCase()}`,
        points: initialPoints,
        partner_id: partnerId,
        program_id: LOYALTY_PROGRAM_ID,
        write_date: "2025-01-01 10:00:00",
    });
}

definePosModels();

function getSplitOrders(store, originOrder) {
    return store.models["pos.order"].filter(
        (order) => order.split_origin_order_id?.uuid === originOrder.uuid
    );
}

async function splitAndPayAs(store, originOrder, partner, amount) {
    const previousSplitOrders = getSplitOrders(store, originOrder);
    originOrder.setPartner(partner);
    await animationFrame();
    await Utils.splitAndPay("Card", amount);
    const splitOrder = getSplitOrders(store, originOrder).find(
        (order) => !previousSplitOrders.includes(order)
    );
    expect(splitOrder.state).toBe("paid");
    await Utils.clickNextOrder();
    return splitOrder;
}

function loyaltySummary(program, order) {
    return {
        partnerId: order.getPartner()?.id || false,
        earned: program.getEarnedPoints(order),
        newBalance: program.getNewBalance(order),
    };
}

describe("SplitPayment - Loyalty", () => {
    let store;
    let program;
    let partners;

    beforeEach(async () => {
        store = await setupAndMountPosApp({ set_tip_after_payment: false });
        deactivateAllProgramsExcept(store, [LOYALTY_PROGRAM_ID]);
        program = store.models["loyalty.program"].get(LOYALTY_PROGRAM_ID);
        partners = Object.fromEntries(
            Object.entries(GUESTS).map(([name, { partnerId }]) => [
                name,
                store.models["res.partner"].get(partnerId),
            ])
        );
        await store.loadPartnerCards(Object.values(GUESTS).map((g) => g.partnerId));
    });

    test("Each guest earns loyalty points on their own share of a split payment", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);

        const originOrder = store.getOrder();
        expect(originOrder.priceIncl).toBe(37);
        await Utils.clickPayButton();

        originOrder.setPartner(partners.alice);
        await animationFrame();
        await Utils.splitAndPay("Card", "10");
        const [aliceOrder] = getSplitOrders(store, originOrder);
        expect(aliceOrder.state).toBe("paid");
        expect(loyaltySummary(program, aliceOrder)).toEqual({
            partnerId: GUESTS.alice.partnerId,
            earned: 10,
            newBalance: GUESTS.alice.initialPoints + 10,
        });

        expect(originOrder.partner_id?.id).toBe(undefined);
        await Utils.clickNextOrder();
        expect(store.getOrder().uuid).toBe(originOrder.uuid);

        originOrder.setPartner(partners.bob);
        await animationFrame();
        await Utils.splitAndPay("Card", "12");
        const bobOrder = getSplitOrders(store, originOrder).find((o) => o !== aliceOrder);
        expect(bobOrder.state).toBe("paid");
        expect(loyaltySummary(program, bobOrder)).toEqual({
            partnerId: GUESTS.bob.partnerId,
            earned: 12,
            newBalance: GUESTS.bob.initialPoints + 12,
        });

        expect(loyaltySummary(program, aliceOrder).earned).toBe(10);
        await Utils.clickNextOrder();

        originOrder.setPartner(partners.carol);
        await animationFrame();
        expect(originOrder.amountAlreadySplitPaid).toBe(22);
        expect(loyaltySummary(program, originOrder)).toEqual({
            partnerId: GUESTS.carol.partnerId,
            earned: 15,
            newBalance: GUESTS.carol.initialPoints + 15,
        });
        await Utils.clickPaymentMethod("Card");
        await Utils.clickValidatePayment();
        expect(originOrder.state).toBe("paid");

        const totalEarned = [aliceOrder, bobOrder, originOrder].reduce(
            (total, order) => total + program.getEarnedPoints(order),
            0
        );
        expect(totalEarned).toBe(37);
    });

    test("A guest without customer earns no points and does not affect the other guests", async () => {
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);
        const originOrder = store.getOrder();
        await Utils.clickPayButton();

        await Utils.splitAndPay("Card", "7");
        const [anonymousOrder] = getSplitOrders(store, originOrder);
        expect(anonymousOrder.state).toBe("paid");
        expect(loyaltySummary(program, anonymousOrder)).toEqual({
            partnerId: false,
            earned: 0,
            newBalance: 0,
        });
        await Utils.clickNextOrder();

        originOrder.setPartner(partners.alice);
        await animationFrame();
        expect(loyaltySummary(program, originOrder)).toEqual({
            partnerId: GUESTS.alice.partnerId,
            earned: 30,
            newBalance: GUESTS.alice.initialPoints + 30,
        });
        await Utils.clickPaymentMethod("Card");
        await Utils.clickValidatePayment();
        expect(originOrder.state).toBe("paid");
    });

    test("Points per order: each split payment order earns the points of an order", async () => {
        program.rule_ids[0].reward_point_mode = "order";
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);
        const originOrder = store.getOrder();
        await Utils.clickPayButton();

        const aliceOrder = await splitAndPayAs(store, originOrder, partners.alice, "10");
        const bobOrder = await splitAndPayAs(store, originOrder, partners.bob, "12");
        originOrder.setPartner(partners.carol);
        await animationFrame();

        expect(loyaltySummary(program, aliceOrder)).toEqual({
            partnerId: GUESTS.alice.partnerId,
            earned: 1,
            newBalance: GUESTS.alice.initialPoints + 1,
        });
        expect(loyaltySummary(program, bobOrder)).toEqual({
            partnerId: GUESTS.bob.partnerId,
            earned: 1,
            newBalance: GUESTS.bob.initialPoints + 1,
        });
        expect(loyaltySummary(program, originOrder)).toEqual({
            partnerId: GUESTS.carol.partnerId,
            earned: 1,
            newBalance: GUESTS.carol.initialPoints + 1,
        });
        await Utils.clickPaymentMethod("Card");
        await Utils.clickValidatePayment();
        expect(originOrder.state).toBe("paid");
    });

    test("Points per unit: split payment lines are ignored, the last guest earns all the units", async () => {
        program.rule_ids[0].reward_point_mode = "unit";
        await Utils.clickTable("1");
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productA20);
        await Utils.clickDisplayedProduct(productB25);
        const originOrder = store.getOrder();
        expect(originOrder.priceIncl).toBe(49);
        await Utils.clickPayButton();

        const aliceOrder = await splitAndPayAs(store, originOrder, partners.alice, "10");
        const bobOrder = await splitAndPayAs(store, originOrder, partners.bob, "12");
        originOrder.setPartner(partners.carol);
        await animationFrame();

        expect(loyaltySummary(program, aliceOrder)).toEqual({
            partnerId: GUESTS.alice.partnerId,
            earned: 0,
            newBalance: GUESTS.alice.initialPoints,
        });
        expect(loyaltySummary(program, bobOrder)).toEqual({
            partnerId: GUESTS.bob.partnerId,
            earned: 0,
            newBalance: GUESTS.bob.initialPoints,
        });
        expect(originOrder.splitPaymentLines.length).toBeGreaterThan(0);
        expect(loyaltySummary(program, originOrder)).toEqual({
            partnerId: GUESTS.carol.partnerId,
            earned: 3,
            newBalance: GUESTS.carol.initialPoints + 3,
        });
        await Utils.clickPaymentMethod("Card");
        await Utils.clickValidatePayment();
        expect(originOrder.state).toBe("paid");
    });
});
