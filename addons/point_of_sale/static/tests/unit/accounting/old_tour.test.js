/**
 * This file contains old tour tests related to accounting that were migrated to Hoot.
 * These tours were not checking anything on the Python side, so they were simply
 * converted to Hoot tests without any additional checks.
 */

import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { prepareRoundingVals } from "./utils";

definePosModels();

test("[Old Tour] pos_basic_order_01_multi_payment_and_change", async () => {
    const store = await setupPosEnv();
    const product1 = store.models["product.template"].get(15);
    product1.list_price = 5.1;
    product1.product_variant_ids[0].lst_price = 5.1;
    product1.taxes_id = [];

    const cashPm = store.models["pos.payment.method"].find((pm) => pm.is_cash_count);
    const cardPm = store.models["pos.payment.method"].find((pm) => !pm.is_cash_count);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    // Add products
    await store.addLineToOrder({ product_tmpl_id: product1, qty: 2 }, order);
    order.addPaymentline(cashPm);
    order.payment_ids[0].setAmount(5);
    expect(order.remainingDue).toBe(5.2);

    order.addPaymentline(cardPm);
    order.payment_ids[1].setAmount(6);
    expect(order.change).toBe(-0.8);
});

test("[Old Tour] PaymentScreenRoundingHalfUp", async () => {
    const store = await setupPosEnv();
    const product1_2 = store.models["product.template"].get(12);
    const product1_25 = store.models["product.template"].get(13);
    const product1_40 = store.models["product.template"].get(14);
    const { cashPm } = prepareRoundingVals(store, 0.5, "HALF-UP", true);

    product1_2.list_price = 1.2;
    product1_2.product_variant_ids[0].lst_price = 1.2;
    product1_2.taxes_id = [];
    product1_25.list_price = 1.25;
    product1_25.product_variant_ids[0].lst_price = 1.25;
    product1_25.taxes_id = [];
    product1_40.list_price = 1.4;
    product1_40.product_variant_ids[0].lst_price = 1.4;
    product1_40.taxes_id = [];

    const order = store.addNewOrder();
    order.pricelist_id = false;
    await store.addLineToOrder({ product_tmpl_id: product1_2, qty: 1 }, order);
    expect(order.totalDue).toBe(1.2);
    order.addPaymentline(cashPm);
    expect(order.amountPaid).toBe(1.0);
    expect(order.appliedRounding).toBe(-0.2);
    expect(order.change).toBe(0.0);

    const order2 = store.addNewOrder();
    order2.pricelist_id = false;
    await store.addLineToOrder({ product_tmpl_id: product1_25, qty: 1 }, order2);
    expect(order2.totalDue).toBe(1.25);
    order2.addPaymentline(cashPm);
    expect(order2.amountPaid).toBe(1.5);
    expect(order2.appliedRounding).toBe(0.25);
    expect(order2.change).toBe(0.0);

    const order3 = store.addNewOrder();
    order3.pricelist_id = false;
    await store.addLineToOrder({ product_tmpl_id: product1_40, qty: 1 }, order3);
    expect(order3.totalDue).toBe(1.4);
    order3.addPaymentline(cashPm);
    expect(order3.amountPaid).toBe(1.5);
    expect(order3.appliedRounding).toBe(0.1);
    expect(order3.change).toBe(0.0);

    const order4 = store.addNewOrder();
    order4.pricelist_id = false;
    await store.addLineToOrder({ product_tmpl_id: product1_2, qty: 1 }, order4);
    expect(order4.totalDue).toBe(1.2);
    order4.addPaymentline(cashPm);
    order4.payment_ids[0].setAmount(2);
    expect(order4.amountPaid).toBe(2.0);
    expect(order4.change).toBe(-1.0);
});

const prepareProduct = (store) => {
    const product = store.models["product.template"].get(15);
    const tax15 = store.models["account.tax"].get(1);
    product.list_price = 13.67;
    product.product_variant_ids[0].lst_price = 13.67;
    product.taxes_id = [tax15];
    return product;
};

test("[Old Tour] test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method", async () => {
    const store = await setupPosEnv();
    const { cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", false);
    const product = prepareProduct(store);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    expect(order.displayPrice).toBe(15.72);
    expect(order.priceExcl).toBe(13.67);
    expect(order.totalDue).toBe(15.7);
    order.addPaymentline(cardPm);
    expect(order.amountPaid).toBe(15.7);
    expect(order.appliedRounding).toBe(-0.02);
    expect(order.change).toBe(0.0);

    const order2 = store.addNewOrder();
    order2.pricelist_id = false;
    order.is_refund = true;
    await store.addLineToOrder({ product_tmpl_id: product, qty: -1 }, order2);
    expect(order2.displayPrice).toBe(-15.72);
    expect(order2.priceExcl).toBe(-13.67);
    expect(order2.totalDue).toBe(-15.7);
    order2.addPaymentline(cardPm);
    expect(order2.amountPaid).toBe(-15.7);
    expect(order2.appliedRounding).toBe(0.02);
    expect(order2.change).toBe(0.0);
});

test("[Old Tour] test_cash_rounding_halfup_add_invoice_line_not_only_round_cash_method_pay_by_bank_and_cash", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", false);
    const product = prepareProduct(store);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    expect(order.displayPrice).toBe(15.72);
    expect(order.priceExcl).toBe(13.67);
    expect(order.totalDue).toBe(15.7);
    order.addPaymentline(cardPm);
    order.payment_ids[0].setAmount(0.68);
    expect(order.amountPaid).toBe(0.68);
    expect(order.remainingDue).toBe(15.02); // Order is rounded globaly so remaining due is rounded
    order.addPaymentline(cashPm);
    expect(order.payment_ids[1].amount).toBe(15.02);
    expect(order.amountPaid).toBe(15.7);
    expect(order.appliedRounding).toBe(-0.02);
    expect(order.change).toBe(0.0);

    const order2 = store.addNewOrder();
    order2.pricelist_id = false;
    order2.is_refund = true;
    await store.addLineToOrder({ product_tmpl_id: product, qty: -1 }, order2);
    expect(order2.displayPrice).toBe(-15.72);
    expect(order2.priceExcl).toBe(-13.67);
    expect(order2.totalDue).toBe(-15.7);
    order2.addPaymentline(cardPm);
    order2.payment_ids[0].setAmount(-0.68);
    expect(order2.amountPaid).toBe(-0.68);
    expect(order2.remainingDue).toBe(-15.02); // Order is rounded globaly so remaining due is rounded
    order2.addPaymentline(cashPm);
    expect(order2.payment_ids[1].amount).toBe(-15.02);
    expect(order2.amountPaid).toBe(-15.7);
    expect(order2.appliedRounding).toBe(0.02);
    expect(order2.change).toBe(0.0);
});

test("[Old Tour] test_cash_rounding_down_add_invoice_line_not_only_round_cash_method_no_rounding_left", async () => {
    const store = await setupPosEnv();
    const { cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", false);
    const product = prepareProduct(store);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    expect(order.displayPrice).toBe(15.72);
    expect(order.priceExcl).toBe(13.67);
    expect(order.totalDue).toBe(15.7);
    order.addPaymentline(cardPm);
    order.payment_ids[0].setAmount(0.67);
    expect(order.amountPaid).toBe(0.67);
    expect(order.remainingDue).toBe(15.03);
    order.addPaymentline(cardPm);
    expect(order.payment_ids[1].amount).toBe(15.03);
    expect(order.amountPaid).toBe(15.7);
    expect(order.appliedRounding).toBe(-0.02);
    expect(order.change).toBe(0.0);

    const order2 = store.addNewOrder();
    order2.pricelist_id = false;
    order2.is_refund = true;
    await store.addLineToOrder({ product_tmpl_id: product, qty: -1 }, order2);
    expect(order2.displayPrice).toBe(-15.72);
    expect(order2.priceExcl).toBe(-13.67);
    expect(order2.totalDue).toBe(-15.7);
    order2.addPaymentline(cardPm);
    order2.payment_ids[0].setAmount(-0.67);
    expect(order2.amountPaid).toBe(-0.67);
    expect(order2.remainingDue).toBe(-15.03);
    order2.addPaymentline(cardPm);
    expect(order2.payment_ids[1].amount).toBe(-15.03);
    expect(order2.amountPaid).toBe(-15.7);
    expect(order2.appliedRounding).toBe(0.02);
    expect(order2.change).toBe(0.0);
});

test("[Old Tour] test_cash_rounding_halfup_add_invoice_line_only_round_cash_method", async () => {
    const store = await setupPosEnv();
    const { cashPm } = prepareRoundingVals(store, 0.05, "HALF-UP", true);
    const product = prepareProduct(store);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    expect(order.displayPrice).toBe(15.72);
    expect(order.priceExcl).toBe(13.67);
    expect(order.totalDue).toBe(15.72);
    order.addPaymentline(cashPm);
    expect(order.amountPaid).toBe(15.7);
    expect(order.appliedRounding).toBe(-0.02);
    expect(order.change).toBe(0.0);

    const order2 = store.addNewOrder();
    order2.pricelist_id = false;
    order2.is_refund = true;
    await store.addLineToOrder({ product_tmpl_id: product, qty: -1 }, order2);
    expect(order2.displayPrice).toBe(-15.72);
    expect(order2.priceExcl).toBe(-13.67);
    expect(order2.totalDue).toBe(-15.72);
    order2.addPaymentline(cashPm);
    expect(order2.amountPaid).toBe(-15.7);
    expect(order2.appliedRounding).toBe(0.02);
    expect(order2.change).toBe(0.0);
});

test("[Old Tour] test_cash_rounding_halfup_add_invoice_line_only_round_cash_method_pay_by_bank_and_cash", async () => {
    const store = await setupPosEnv();
    const { cashPm, cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", true);
    const product = prepareProduct(store);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    expect(order.displayPrice).toBe(15.72);
    expect(order.priceExcl).toBe(13.67);
    expect(order.totalDue).toBe(15.72);
    order.addPaymentline(cardPm);
    order.payment_ids[0].setAmount(0.68);
    expect(order.amountPaid).toBe(0.68);
    expect(order.remainingDue).toBe(15.04);
    order.addPaymentline(cashPm);
    expect(order.payment_ids[1].amount).toBe(15.05);
    expect(order.amountPaid).toBe(15.73);
    expect(order.appliedRounding).toBe(0.01);
    expect(order.change).toBe(0.0);

    const order2 = store.addNewOrder();
    order2.pricelist_id = false;
    order2.is_refund = true;
    await store.addLineToOrder({ product_tmpl_id: product, qty: -1 }, order2);
    expect(order2.displayPrice).toBe(-15.72);
    expect(order2.priceExcl).toBe(-13.67);
    expect(order2.totalDue).toBe(-15.72);
    order2.addPaymentline(cardPm);
    order2.payment_ids[0].setAmount(-0.68);
    expect(order2.amountPaid).toBe(-0.68);
    expect(order2.remainingDue).toBe(-15.04);
    order2.addPaymentline(cashPm);
    expect(order2.payment_ids[1].amount).toBe(-15.05);
    expect(order2.amountPaid).toBe(-15.73);
    expect(order2.appliedRounding).toBe(-0.01);
    expect(order2.change).toBe(0.0);
});

test("[Old Tour] test_cash_rounding_with_change", async () => {
    const store = await setupPosEnv();
    const { cardPm } = prepareRoundingVals(store, 0.05, "HALF-UP", false);
    const product = prepareProduct(store);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    expect(order.displayPrice).toBe(15.72);
    expect(order.priceExcl).toBe(13.67);
    expect(order.totalDue).toBe(15.7);
    order.addPaymentline(cardPm);
    order.payment_ids[0].setAmount(20);
    expect(order.amountPaid).toBe(20);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(-4.3);

    const order2 = store.addNewOrder();
    order2.pricelist_id = false;
    order2.is_refund = true;
    await store.addLineToOrder({ product_tmpl_id: product, qty: -1 }, order2);
    expect(order2.displayPrice).toBe(-15.72);
    expect(order2.priceExcl).toBe(-13.67);
    expect(order2.totalDue).toBe(-15.7);
    order2.addPaymentline(cardPm);
    order2.payment_ids[0].setAmount(-20);
    expect(order2.amountPaid).toBe(-20);
    expect(order2.appliedRounding).toBe(0);
    expect(order2.change).toBe(4.3);
});

test("[Old Tour] test_cash_rounding_only_cash_method_with_change", async () => {
    const store = await setupPosEnv();
    const { cashPm } = prepareRoundingVals(store, 0.05, "HALF-UP", true);
    const product = prepareProduct(store);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    expect(order.displayPrice).toBe(15.72);
    expect(order.priceExcl).toBe(13.67);
    expect(order.totalDue).toBe(15.72);
    order.addPaymentline(cashPm);
    order.payment_ids[0].setAmount(20);
    expect(order.amountPaid).toBe(20);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(-4.3);

    const order2 = store.addNewOrder();
    order2.pricelist_id = false;
    order2.is_refund = true;
    await store.addLineToOrder({ product_tmpl_id: product, qty: -1 }, order2);
    expect(order2.displayPrice).toBe(-15.72);
    expect(order2.priceExcl).toBe(-13.67);
    expect(order2.totalDue).toBe(-15.72);
    order2.addPaymentline(cashPm);
    order2.payment_ids[0].setAmount(-20);
    expect(order2.amountPaid).toBe(-20);
    expect(order2.appliedRounding).toBe(0);
    expect(order2.change).toBe(4.3);
});

test(["[Old Tour] test_cash_rounding_up_with_change"], async () => {
    const store = await setupPosEnv();
    const { cashPm } = prepareRoundingVals(store, 1, "UP", true);
    const order = store.addNewOrder();
    order.pricelist_id = false;

    const tax = store.models["account.tax"].get(3);
    const productA = store.models["product.template"].get(15);
    const productB = store.models["product.template"].get(16);
    productA.list_price = 95;
    productA.product_variant_ids[0].lst_price = 95;
    productA.taxes_id = [tax];
    productB.list_price = 42;
    productB.product_variant_ids[0].lst_price = 42;
    productB.taxes_id = [tax];

    await store.addLineToOrder({ product_tmpl_id: productA, qty: 1 }, order);
    await store.addLineToOrder({ product_tmpl_id: productB, qty: 2 }, order);

    expect(order.displayPrice).toBe(179);
    expect(order.totalDue).toBe(179);
    order.addPaymentline(cashPm);
    order.payment_ids[0].setAmount(200);
    expect(order.amountPaid).toBe(200);
    expect(order.appliedRounding).toBe(0);
    expect(order.change).toBe(-21);
});
