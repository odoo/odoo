odoo.define('point_of_sale.unit.test_Rounding_DOWN', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const webClient = require('web.web_client');
    const RamStorage = require('web.RamStorage');
    const { createCheckPayment } = require('point_of_sale.unit.utils');

    let model, cashPaymentMethod, bankPaymentMethod, product1;

    QUnit.module('invariants for rounding UP by 0.05', {
        async before() {
            model = new PointOfSaleModel(webClient, 100, new RamStorage());
            await model.loadPosData();
            cashPaymentMethod = model.data.derived.paymentMethods.find((method) => method.name === 'Cash');
            bankPaymentMethod = model.data.derived.paymentMethods.find((method) => method.name === 'Bank');
            product1 = model.getProducts(0)[0];
        },
        beforeEach() {
            model.storage.clear();
            for (const order of model.getOrders(() => true)) {
                model.deleteOrder(order.id);
            }
        },
    });

    QUnit.test('preamble', async function (assert) {
        assert.expect(5);
        assert.ok(model);
        assert.ok(cashPaymentMethod);
        assert.ok(bankPaymentMethod);
        assert.ok(product1);
        assert.ok(model.data.derived.roundingScheme === 'ONLY_CASH_ROUNDING');
    });

    QUnit.test('invariants for rounding UP by 0.05', async function (assert) {
        assert.expect(173);
        let payment1, payment2, payment3, payment4, payment5;
        await model.actionCreateNewOrder();
        const activeOrder = model.getActiveOrder();
        const orderline = await model.actionAddProduct(activeOrder, product1, {});
        await model.actionUpdateOrderline(orderline, { price_unit: 12.13 });

        const amountToPay = model.getAmountToPay(activeOrder);
        assert.ok(model.monetaryEQ(amountToPay, 12.13));

        const checkPayment = createCheckPayment(assert, model, activeOrder);

        // case 1
        payment1 = await model.actionAddPayment(activeOrder, cashPaymentMethod);
        checkPayment('case1', payment1, {
            amount: 12.15,
            orderIsPaid: true,
            remaining: 0,
            change: 0,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);

        // case 2
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod);
        checkPayment('case2', payment1, {
            amount: 12.13,
            orderIsPaid: true,
            remaining: 0,
            change: 0,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);

        // case 3
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 9.99);
        checkPayment('case3_1', payment1, {
            amount: 9.99,
            orderIsPaid: false,
            remaining: 2.14,
            change: 0,
            paymentIsValid: true,
        });
        payment2 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 2.2);
        checkPayment('case3_2', payment2, {
            amount: 2.2,
            orderIsPaid: true,
            remaining: 0,
            change: 0.05,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);
        await model.actionDeletePayment(payment2);

        // case 4
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 9.99);
        checkPayment('case4_1', payment1, {
            amount: 9.99,
            orderIsPaid: false,
            remaining: 2.14,
            change: 0,
            paymentIsValid: true,
        });
        payment2 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 2.15);
        checkPayment('case4_2', payment2, {
            amount: 2.15,
            orderIsPaid: true,
            remaining: 0,
            change: 0,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);
        await model.actionDeletePayment(payment2);

        // case 5
        payment1 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 10.01);
        checkPayment('case5', payment1, {
            amount: 10.01,
            orderIsPaid: false,
            remaining: 2.12,
            change: 0,
            paymentIsValid: false,
        });
        // We don't prevent addition of new payment even if the previous payment
        // is already invalid. Check is done by the event handler when clicking
        // the button that calls actionAddPayment.
        payment2 = await model.actionAddPayment(activeOrder, bankPaymentMethod);
        checkPayment('case5_2', payment2, {
            amount: 2.12,
            orderIsPaid: true,
            remaining: 0,
            change: 0,
            paymentIsValid: true,
        });
        assert.ok(
            model.getInvalidRoundingPayment(activeOrder) === payment1,
            'case5_1: payment1 is the invalid payment of the order'
        );
        await model.actionDeletePayment(payment1);
        await model.actionDeletePayment(payment2);

        // case 6
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 10.01);
        checkPayment('case6_1', payment1, {
            amount: 10.01,
            orderIsPaid: false,
            remaining: 2.12,
            change: 0,
            paymentIsValid: true,
        });
        payment2 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 2.1);
        checkPayment('case6_2', payment2, {
            amount: 2.1,
            orderIsPaid: false,
            remaining: 0.02,
            change: 0,
            paymentIsValid: true,
        });
        payment3 = await model.actionAddPayment(activeOrder, cashPaymentMethod);
        checkPayment('case6_3', payment3, {
            amount: 0.05,
            orderIsPaid: true,
            remaining: 0,
            change: 0,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);
        await model.actionDeletePayment(payment2);
        await model.actionDeletePayment(payment3);

        // case 7
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 20);
        checkPayment('case7', payment1, {
            amount: 20,
            orderIsPaid: true,
            remaining: 0,
            change: 7.85,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);

        // case 8
        payment1 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 20);
        checkPayment('case8', payment1, {
            amount: 20,
            orderIsPaid: true,
            remaining: 0,
            change: 7.85,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);

        // case 9
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 20.01);
        checkPayment('case9', payment1, {
            amount: 20.01,
            orderIsPaid: true,
            remaining: 0,
            change: 7.85,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);

        // case 10
        payment1 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 20.01);
        checkPayment('case10', payment1, {
            amount: 20.01,
            orderIsPaid: true,
            remaining: 0,
            change: 7.85,
            paymentIsValid: false,
        });
        await model.actionDeletePayment(payment1);

        // case 11
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 1.01);
        checkPayment('case11_1', payment1, {
            amount: 1.01,
            orderIsPaid: false,
            remaining: 11.12,
            change: 0,
            paymentIsValid: true,
        });
        payment2 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 1.0);
        checkPayment('case11_2', payment2, {
            amount: 1.0,
            orderIsPaid: false,
            remaining: 10.12,
            change: 0,
            paymentIsValid: true,
        });
        payment3 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 2.99);
        checkPayment('case11_3', payment3, {
            amount: 2.99,
            orderIsPaid: false,
            remaining: 7.13,
            change: 0,
            paymentIsValid: true,
        });
        payment4 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 1.01);
        checkPayment('case11_4', payment4, {
            amount: 1.01,
            orderIsPaid: false,
            remaining: 6.12,
            change: 0,
            paymentIsValid: false,
        });
        payment5 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 6.1);
        checkPayment('case11_5', payment5, {
            amount: 6.1,
            orderIsPaid: false,
            remaining: 0.02,
            change: 0,
            paymentIsValid: true,
        });
        assert.ok(
            model.getInvalidRoundingPayment(activeOrder) === payment4,
            'case11_5: payment5 is the invalid payment of the order'
        );
        await model.actionDeletePayment(payment1);
        await model.actionDeletePayment(payment2);
        await model.actionDeletePayment(payment3);
        await model.actionDeletePayment(payment4);
        await model.actionDeletePayment(payment5);

        // case 12
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 1.01);
        checkPayment('case12_1', payment1, {
            amount: 1.01,
            orderIsPaid: false,
            remaining: 11.12,
            change: 0,
            paymentIsValid: true,
        });
        payment2 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 5.0);
        checkPayment('case12_2', payment2, {
            amount: 5.0,
            orderIsPaid: false,
            remaining: 6.12,
            change: 0,
            paymentIsValid: true,
        });
        payment3 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 2.21);
        checkPayment('case12_3', payment3, {
            amount: 2.21,
            orderIsPaid: false,
            remaining: 3.91,
            change: 0,
            paymentIsValid: true,
        });
        payment4 = await model.actionAddPayment(activeOrder, cashPaymentMethod);
        checkPayment('case12_4', payment4, {
            amount: 3.95,
            orderIsPaid: true,
            remaining: 0,
            change: 0,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);
        await model.actionDeletePayment(payment2);
        await model.actionDeletePayment(payment3);
        await model.actionDeletePayment(payment4);

        // case 13
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 1.01);
        checkPayment('case13_1', payment1, {
            amount: 1.01,
            orderIsPaid: false,
            remaining: 11.12,
            change: 0,
            paymentIsValid: true,
        });
        payment2 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 5.0);
        checkPayment('case13_2', payment2, {
            amount: 5.0,
            orderIsPaid: false,
            remaining: 6.12,
            change: 0,
            paymentIsValid: true,
        });
        payment3 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 2.21);
        checkPayment('case13_3', payment3, {
            amount: 2.21,
            orderIsPaid: false,
            remaining: 3.91,
            change: 0,
            paymentIsValid: true,
        });
        payment4 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 3.9);
        checkPayment('case13_4', payment4, {
            amount: 3.9,
            orderIsPaid: false,
            remaining: 0.01,
            change: 0,
            paymentIsValid: true,
        });
        payment5 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 0.1);
        checkPayment('case13_5', payment5, {
            amount: 0.1,
            orderIsPaid: true,
            remaining: 0,
            change: 0.05,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);
        await model.actionDeletePayment(payment2);
        await model.actionDeletePayment(payment3);
        await model.actionDeletePayment(payment4);
        await model.actionDeletePayment(payment5);

        // case 14
        payment1 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 1.01);
        checkPayment('case14_1', payment1, {
            amount: 1.01,
            orderIsPaid: false,
            remaining: 11.12,
            change: 0,
            paymentIsValid: true,
        });
        payment2 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 5.0);
        checkPayment('case14_2', payment2, {
            amount: 5.0,
            orderIsPaid: false,
            remaining: 6.12,
            change: 0,
            paymentIsValid: true,
        });
        payment3 = await model.actionAddPayment(activeOrder, bankPaymentMethod, 2.21);
        checkPayment('case14_3', payment3, {
            amount: 2.21,
            orderIsPaid: false,
            remaining: 3.91,
            change: 0,
            paymentIsValid: true,
        });
        payment4 = await model.actionAddPayment(activeOrder, cashPaymentMethod, 3.85);
        checkPayment('case14_4', payment4, {
            amount: 3.85,
            orderIsPaid: false,
            remaining: 0.06,
            change: 0,
            paymentIsValid: true,
        });
        payment5 = await model.actionAddPayment(activeOrder, bankPaymentMethod);
        checkPayment('case14_5', payment5, {
            amount: 0.06,
            orderIsPaid: true,
            remaining: 0,
            change: 0,
            paymentIsValid: true,
        });
        await model.actionDeletePayment(payment1);
        await model.actionDeletePayment(payment2);
        await model.actionDeletePayment(payment3);
        await model.actionDeletePayment(payment4);
        await model.actionDeletePayment(payment5);
    });
});
