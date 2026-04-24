import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { prepareRoundingVals, getSingleProductOrder } from "../accounting/utils";
import { imageDataUri } from "@point_of_sale/utils";
import {
    renameProduct,
    setProductPrice,
    addPayment,
    renderReceipt,
    expectReceiptPayload,
    expectTicketData,
    setTipAfterPaymentConfig,
} from "../receipt_utils";

definePosModels();

test("ticket data renders totals, cashier, payments, order lines and qr code", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const cardPm = store.models["pos.payment.method"].get(2);

    renameProduct(product, "Desk Pad");
    cardPm.name = "Bank";
    store.user.name = "Mitchell Admin";
    await store.addLineToOrder({ product_tmpl_id: product, qty: 3 }, order);
    addPayment(order, cardPm, 10.35);
    order.setOrderPrices();

    const { ticket } = renderReceipt(store, order);

    expectTicketData(ticket, {
        total_amount: "$ 10.35",
        cashier_name: "Mitchell",
        is_to_pay: true,
        is_change: false,
        is_qr_code: true,
        payment_lines: [{ name: "Bank", amount: "10.35" }],
        orderlines: [
            {
                name: "Desk Pad",
                quantity: "3",
                price_unit: "3.45",
                line_price: "$ 10.35",
            },
        ],
        cssRules: [
            {
                css: "tbody[name='company_info']",
                text: "Hoot",
            },
        ],
    });
});

test("ticket data renders tip lines and line css rules", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const tipProduct = store.models["product.template"].get(1);
    const cardPm = store.models["pos.payment.method"].get(2);

    renameProduct(product, "Desk Pad");
    renameProduct(tipProduct, "Tips");
    cardPm.name = "Bank";

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 3 }, order);
    line.setCustomerNote("Test customer note");
    const tipLine = await store.addLineToOrder({ product_tmpl_id: tipProduct, qty: 1 }, order);
    tipLine.setUnitPrice(1);
    tipLine.price_type = "manual";
    addPayment(order, cardPm, 7);

    const { ticket } = renderReceipt(store, order);
    expectTicketData(ticket, {
        total_amount: "$ 11.35",
        payment_lines: [{ name: "Bank", amount: "7.00" }],
        orderlines: [
            {
                name: "Desk Pad",
                quantity: "3",
                price_unit: "3.45",
                line_price: "$ 10.35",
                cssRules: [
                    {
                        css: ".line-note",
                        text: "Test customer note",
                    },
                ],
            },
            {
                name: "Tips",
                quantity: "1",
                price_unit: "1.00",
                line_price: "1.00",
            },
        ],
    });
});

test("ticket data does not render internal notes", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const cardPm = store.models["pos.payment.method"].get(2);

    setProductPrice(product, 10, []);
    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setNote('[{"text":"Test internal note","colorIndex":0}]');
    order.setInternalNote("Test internal note on order");
    addPayment(order, cardPm, 10);

    const { ticket } = renderReceipt(store, order);
    expectTicketData(ticket, {
        orderlines: [
            {
                name: "TEST",
                cssRules: [
                    {
                        css: ".o_tag_badge_text",
                        text: "Test internal note",
                        negation: true,
                    },
                ],
            },
        ],
        cssRules: [
            {
                css: ".internal-note-container",
                text: "Test internal note on order",
                negation: true,
            },
        ],
    });
});

test("ticket data renders discount details and can omit discount summary for manual prices", async () => {
    const store = await setupPosEnv();
    const product = store.models["product.template"].get(5);
    const cardPm = store.models["pos.payment.method"].get(2);

    const discountedOrder = store.addNewOrder();
    const discountedLine = await store.addLineToOrder(
        { product_tmpl_id: product, qty: 1 },
        discountedOrder
    );
    discountedLine.setDiscount(5);
    addPayment(discountedOrder, cardPm, 3.28);

    const { ticket: discountedTicket } = renderReceipt(store, discountedOrder);
    expectTicketData(discountedTicket, {
        total_amount: "$ 3.28",
        is_discount: true,
        orderlines: [
            {
                name: "TEST",
                quantity: "1",
                line_price: "$ 3.28",
            },
        ],
    });

    const manualPriceOrder = store.addNewOrder();
    const manualLine = await store.addLineToOrder(
        { product_tmpl_id: product, qty: 1 },
        manualPriceOrder
    );
    manualLine.setUnitPrice(9);
    manualLine.price_type = "manual";
    addPayment(manualPriceOrder, cardPm, 10.35);

    const { ticket: manualPriceTicket } = renderReceipt(store, manualPriceOrder);
    expectTicketData(manualPriceTicket, {
        total_amount: "$ 10.35",
        is_discount: false,
        orderlines: [
            {
                name: "TEST",
                quantity: "1",
                line_price: "$ 10.35",
            },
        ],
    });
});

test("ticket data renders receipt change on overpayment", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const cashPm = store.models["pos.payment.method"].get(1);

    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    addPayment(order, cashPm, 5);
    order.setOrderPrices();

    const { ticket } = renderReceipt(store, order);
    expectTicketData(ticket, {
        total_amount: "$ 3.45",
        is_change: true,
        change_amount: "-1.55",
    });
});

test("ticket data renders rounding amounts on receipts", async () => {
    const store = await setupPosEnv();

    const { cashPm } = prepareRoundingVals(store, 0.05, "DOWN", true);
    const order = await getSingleProductOrder(store, 1.98);
    expect(order.totalDue).toBe(1.98);
    order.addPaymentline(cashPm);
    order.setOrderPrices();

    const { ticket } = renderReceipt(store, order);
    expectTicketData(ticket, {
        total_amount: "$ 1.95",
        is_rounding: true,
        rounding_amount: "-0.03",
        is_change: false,
    });
});

test("ticket data renders logo and contact info variants", async () => {
    const cases = [
        {
            name: "company logo",
            logo: "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==",
            contact_info: "123456789",
        },
        {
            name: "no logo",
            logo: false,
            contact_info: "123456789",
        },
    ];

    const store = await setupPosEnv();
    for (const receiptCase of cases) {
        const order = store.addNewOrder();
        const product = store.models["product.template"].get(5);

        setProductPrice(product, 5, []);
        store.config.logo = receiptCase.logo;
        store.config.phone = receiptCase.contact_info;
        await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);

        const { ticket } = renderReceipt(store, order);
        expectTicketData(ticket, {
            logo: imageDataUri(receiptCase.logo),
            contact_info: receiptCase.contact_info,
        });
    }
});

test("ticket data can hide the invoice qr code", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    setProductPrice(product, 10, []);
    store.config.company_id.point_of_sale_ticket_portal_url_display_mode = "url";
    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);

    const { ticket } = renderReceipt(store, order);
    expectTicketData(ticket, {
        is_qr_code: false,
    });
});

const tipAfterPaymentCases = [
    {
        name: "15 percent tip",
        qty: 1,
        unitPrice: 2,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 2,
        tipAmount: 0.3,
        totalAmount: "2.30",
        lines: [
            {
                name: "Desk Pad",
                quantity: "1",
                price_unit: "2.00",
                line_price: "2.00",
            },
            { name: "Tips", quantity: "1", price_unit: "0.30", line_price: "0.30" },
        ],
    },
    {
        name: "20 percent tip",
        qty: 2,
        unitPrice: 2,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 4,
        tipAmount: 0.8,
        totalAmount: "4.80",
        lines: [
            {
                name: "Desk Pad",
                quantity: "2",
                price_unit: "2.00",
                line_price: "4.00",
            },
            { name: "Tips", quantity: "1", price_unit: "0.80", line_price: "0.80" },
        ],
    },
    {
        name: "25 percent tip on 6.00 total",
        qty: 3,
        unitPrice: 2,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 6,
        tipAmount: 1.5,
        totalAmount: "7.50",
        lines: [
            {
                name: "Desk Pad",
                quantity: "3",
                price_unit: "2.00",
                line_price: "6.00",
            },
            { name: "Tips", quantity: "1", price_unit: "1.50", line_price: "1.50" },
        ],
    },
    {
        name: "25 percent tip on 8.00 total",
        qty: 4,
        unitPrice: 2,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 8,
        tipAmount: 2,
        totalAmount: "10.00",
        lines: [
            {
                name: "Desk Pad",
                quantity: "4",
                price_unit: "2.00",
                line_price: "8.00",
            },
            { name: "Tips", quantity: "1", price_unit: "2.00", line_price: "2.00" },
        ],
    },
    {
        name: "no tip after tip screen",
        qty: 5,
        unitPrice: 2,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 10,
        totalAmount: "10.00",
        lines: [
            {
                name: "Desk Pad",
                quantity: "5",
                price_unit: "2.00",
                line_price: "10.00",
            },
        ],
    },
    {
        name: "custom tip",
        qty: 6,
        unitPrice: 2,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 12,
        tipAmount: 1,
        totalAmount: "13.00",
        lines: [
            {
                name: "Desk Pad",
                quantity: "6",
                price_unit: "2.00",
                line_price: "12.00",
            },
            { name: "Tips", quantity: "1", price_unit: "1.00", line_price: "1.00" },
        ],
    },
    {
        name: "direct settle without tip",
        qty: 7,
        unitPrice: 2,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 14,
        totalAmount: "14.00",
        lines: [
            {
                name: "Desk Pad",
                quantity: "7",
                price_unit: "2.00",
                line_price: "14.00",
            },
        ],
    },
    {
        name: "cash payment skips tip screen",
        qty: 8,
        unitPrice: 2,
        paymentMethodId: 1,
        paymentName: "Cash",
        paymentAmount: 16,
        totalAmount: "16.00",
        lines: [
            {
                name: "Desk Pad",
                quantity: "8",
                price_unit: "2.00",
                line_price: "16.00",
            },
        ],
    },
    {
        name: "already tipped before validation",
        qty: 4,
        unitPrice: 25,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 110,
        tipAmount: 10,
        tipBeforePayment: true,
        totalAmount: "110.00",
        lines: [
            {
                name: "Desk Pad",
                quantity: "4",
                price_unit: "25.00",
                line_price: "100.00",
            },
            { name: "Tips", quantity: "1", price_unit: "10.00", line_price: "10.00" },
        ],
    },
    {
        name: "deleted tip before tip screen",
        qty: 4,
        unitPrice: 25,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 100,
        initialTipAmount: 25,
        removeTip: true,
        totalAmount: "100.00",
        lines: [
            {
                name: "Desk Pad",
                quantity: "4",
                price_unit: "25.00",
                line_price: "100.00",
            },
        ],
    },
    {
        name: "zero tip before tip screen",
        qty: 4,
        unitPrice: 25,
        paymentMethodId: 2,
        paymentName: "Bank",
        paymentAmount: 100,
        initialTipAmount: 0,
        totalAmount: "100.00",
        lines: [
            {
                name: "Desk Pad",
                quantity: "4",
                price_unit: "25.00",
                line_price: "100.00",
            },
        ],
    },
];

for (const tipCase of tipAfterPaymentCases) {
    test(`ticket data matches tip-after-payment tour case: ${tipCase.name}`, async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const product = store.models["product.template"].get(5);
        const tipProduct = store.models["product.template"].get(1);
        const paymentMethod = store.models["pos.payment.method"].get(tipCase.paymentMethodId);

        setTipAfterPaymentConfig(store);
        renameProduct(product, "Desk Pad");
        renameProduct(tipProduct, "Tips");
        product.update({
            list_price: tipCase.unitPrice,
            taxes_id: [],
        });
        product.product_variant_ids[0].update({
            lst_price: tipCase.unitPrice,
        });
        tipProduct.update({
            list_price: 0,
            taxes_id: [],
        });
        tipProduct.product_variant_ids[0].update({
            lst_price: 0,
        });
        paymentMethod.name = tipCase.paymentName;

        const orderline = await store.addLineToOrder(
            { product_tmpl_id: product, qty: tipCase.qty },
            order
        );
        orderline.setUnitPrice(tipCase.unitPrice);
        orderline.price_type = "manual";
        store.setOrder(order);

        if (tipCase.initialTipAmount !== undefined) {
            await store.setTip(tipCase.initialTipAmount);
        }

        if (tipCase.tipBeforePayment && tipCase.tipAmount !== undefined) {
            await store.setTip(tipCase.tipAmount);
        }

        if (tipCase.removeTip) {
            await store.setTip(false);
        }

        addPayment(order, paymentMethod, tipCase.paymentAmount);

        if (!tipCase.tipBeforePayment && tipCase.tipAmount !== undefined) {
            await store.setTip(tipCase.tipAmount);
        }

        const { data, ticket } = renderReceipt(store, order);
        expectReceiptPayload(data, {
            total_amount: tipCase.totalAmount,
            payment_lines: [
                { name: tipCase.paymentName, amount: tipCase.paymentAmount.toFixed(2) },
            ],
            orderlines: tipCase.lines,
        });
        expectTicketData(ticket, {
            total_amount: tipCase.totalAmount,
            payment_lines: [
                { name: tipCase.paymentName, amount: tipCase.paymentAmount.toFixed(2) },
            ],
            orderlines: tipCase.lines,
        });
    });
}

const cashRoundingCases = [
    {
        name: "all methods sale without rounding",
        price: 15.7,
        onlyRoundCashMethod: false,
        payments: [{ paymentMethodId: 1, amount: 15.7 }],
        totalAmount: "15.70",
        roundingAmount: false,
    },
    {
        name: "all methods refund without rounding",
        price: 15.7,
        onlyRoundCashMethod: false,
        isRefund: true,
        payments: [{ paymentMethodId: 1, amount: -15.7 }],
        totalAmount: "-15.70",
        roundingAmount: false,
    },
    {
        name: "all methods sale with rounding down",
        price: 15.72,
        onlyRoundCashMethod: false,
        payments: [{ paymentMethodId: 1, amount: 15.7 }],
        totalAmount: "15.70",
        roundingAmount: "-0.02",
    },
    {
        name: "all methods refund with rounding up",
        price: 15.72,
        onlyRoundCashMethod: false,
        isRefund: true,
        payments: [{ paymentMethodId: 1, amount: -15.7 }],
        totalAmount: "-15.70",
        roundingAmount: "0.02",
    },
    {
        name: "all methods sale with bank and cash",
        price: 15.7,
        onlyRoundCashMethod: false,
        payments: [
            { paymentMethodId: 2, amount: 0.67 },
            { paymentMethodId: 1, amount: 15.03 },
        ],
        totalAmount: "15.70",
        roundingAmount: false,
    },
    {
        name: "all methods refund with bank and cash",
        price: 15.7,
        onlyRoundCashMethod: false,
        isRefund: true,
        payments: [
            { paymentMethodId: 2, amount: -0.67 },
            { paymentMethodId: 1, amount: -15.03 },
        ],
        totalAmount: "-15.70",
        roundingAmount: false,
    },
    {
        name: "cash only sale with rounding down",
        price: 15.72,
        onlyRoundCashMethod: true,
        payments: [{ paymentMethodId: 1, amount: 15.7 }],
        totalAmount: "15.70",
        roundingAmount: "-0.02",
    },
    {
        name: "cash only refund with rounding up",
        price: 15.72,
        onlyRoundCashMethod: true,
        isRefund: true,
        payments: [{ paymentMethodId: 1, amount: -15.7 }],
        totalAmount: "-15.70",
        roundingAmount: "0.02",
    },
    {
        name: "cash only sale with bank and cash",
        price: 15.72,
        onlyRoundCashMethod: true,
        payments: [
            { paymentMethodId: 2, amount: 0.68 },
            { paymentMethodId: 1, amount: 15.04 },
        ],
        totalAmount: "15.70",
        roundingAmount: false,
    },
    {
        name: "cash only refund with bank and cash",
        price: 15.72,
        onlyRoundCashMethod: true,
        isRefund: true,
        payments: [
            { paymentMethodId: 2, amount: -0.68 },
            { paymentMethodId: 1, amount: -15.04 },
        ],
        totalAmount: "-15.70",
        roundingAmount: false,
    },
];

for (const roundingCase of cashRoundingCases) {
    test(`ticket data matches cash-rounding tour case: ${roundingCase.name}`, async () => {
        const store = await setupPosEnv();

        prepareRoundingVals(store, 0.05, "HALF-UP", roundingCase.onlyRoundCashMethod);
        const order = await getSingleProductOrder(
            store,
            roundingCase.price,
            roundingCase.isRefund
        );
        const expectedLineName = order.lines[0].product_id.display_name;

        const expectedPayments = [];
        for (const payment of roundingCase.payments) {
            const paymentMethod = store.models["pos.payment.method"].get(payment.paymentMethodId);
            expectedPayments.push({
                name: paymentMethod.name,
                amount: payment.amount.toFixed(2),
            });
            addPayment(order, paymentMethod, payment.amount);
        }

        order.setOrderPrices();

        const { data, ticket } = renderReceipt(store, order);
        expectReceiptPayload(data, {
            total_amount: roundingCase.totalAmount,
            rounding_amount: roundingCase.roundingAmount,
            payment_lines: expectedPayments,
            orderlines: [
                {
                    name: expectedLineName,
                    quantity: roundingCase.isRefund ? "-1" : "1",
                    price_unit: Math.abs(roundingCase.price).toFixed(2),
                    line_price: Math.abs(roundingCase.price).toFixed(2),
                },
            ],
        });
        expectTicketData(ticket, {
            total_amount: roundingCase.totalAmount,
            is_rounding: roundingCase.roundingAmount !== false,
            rounding_amount: roundingCase.roundingAmount,
            is_change: false,
            payment_lines: expectedPayments,
        });
    });
}

test("test_printed_receipt_tour: basic receipt hides totals and prices", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    setProductPrice(product, 5, []);
    renameProduct(product, "Desk Pad");
    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);

    const cashPm = store.models["pos.payment.method"].find((pm) => !pm.is_cash_count);
    addPayment(order, cashPm, 5);
    order.setOrderPrices();

    const { data, ticket } = renderReceipt(store, order, true);

    expect(data.conditions.basic_receipt).toBe(true);
    expectTicketData(
        ticket,
        {
            orderlines: [{ name: "Desk Pad", quantity: "1" }],
        },
        true
    );

    expect(Boolean(ticket.querySelector('div[name="prices"]'))).toBe(false);
    expect(Boolean(ticket.querySelector(".price-incl"))).toBe(false);
    expect(Boolean(ticket.querySelector(".price-unit"))).toBe(false);
});

test("custom phone displayed on receipt", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    setProductPrice(product, 5, []);
    store.config.use_custom_receipt_info = true;
    store.config.custom_phone = "555-999";
    store.config.phone = "555-999";
    await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);

    const cashPm = store.models["pos.payment.method"].find((pm) => !pm.is_cash_count);
    addPayment(order, cashPm, 5);
    order.setOrderPrices();

    const { ticket } = renderReceipt(store, order);
    expectTicketData(ticket, {
        contact_info: "555-999",
    });
});
