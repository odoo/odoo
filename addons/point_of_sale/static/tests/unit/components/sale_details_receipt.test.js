import { test } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { renderSaleDetailsReceipt, expectSaleDetailsTicket } from "../receipt_utils";

definePosModels();

const baseSaleDetails = {
    currency: { total_paid: 150 },
    products: [
        {
            name: "Food",
            qty: 5,
            total: 100,
            products: [
                { product_id: 1, product_name: "Burger", quantity: 3, total_paid: 60 },
                { product_id: 2, product_name: "Fries", quantity: 2, total_paid: 40 },
            ],
        },
    ],
    refund_products: [],
    cancelled_products: [],
    payments: [
        { name: "Cash", total: 100 },
        { name: "Bank", total: 50 },
    ],
    taxes: [{ name: "VAT 15%", tax_amount: 19.57 }],
};

test("sale details ticket renders sold products by category", async () => {
    const store = await setupPosEnv();

    const { ticket } = renderSaleDetailsReceipt(store, baseSaleDetails);

    expectSaleDetailsTicket(ticket, {
        is_sold_section: true,
        sold_categories: [{ name: "Food", products: ["Burger", "Fries"] }],
        is_refund_section: false,
        is_company_info: true,
    });
});

test("sale details ticket renders refunded products", async () => {
    const store = await setupPosEnv();

    const details = {
        ...baseSaleDetails,
        refund_products: [
            {
                name: "Drinks",
                qty: 1,
                total: -10,
                products: [{ product_id: 3, product_name: "Soda", quantity: 1, total_paid: -10 }],
            },
        ],
    };

    const { ticket } = renderSaleDetailsReceipt(store, details);

    expectSaleDetailsTicket(ticket, {
        is_sold_section: true,
        is_refund_section: true,
    });
});

test("sale details ticket renders payments section", async () => {
    const store = await setupPosEnv();

    const { ticket } = renderSaleDetailsReceipt(store, baseSaleDetails);

    expectSaleDetailsTicket(ticket, {
        payments: [{ name: "Cash" }, { name: "Bank" }],
    });
});

test("sale details ticket renders taxes section", async () => {
    const store = await setupPosEnv();

    const { ticket } = renderSaleDetailsReceipt(store, baseSaleDetails);

    expectSaleDetailsTicket(ticket, {
        taxes: [{ name: "VAT 15%" }],
    });
});

test("sale details ticket renders total paid", async () => {
    const store = await setupPosEnv();

    const { ticket } = renderSaleDetailsReceipt(store, baseSaleDetails);

    expectSaleDetailsTicket(ticket, {
        total_paid: "150.00",
    });
});

test("sale details ticket renders logo when configured", async () => {
    const store = await setupPosEnv();
    store.config.logo =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==";

    const { ticket } = renderSaleDetailsReceipt(store, baseSaleDetails);

    expectSaleDetailsTicket(ticket, {
        logo: true,
        is_sold_section: true,
        total_paid: "150.00",
    });
});

test("sale details ticket does not render logo when not configured", async () => {
    const store = await setupPosEnv();
    store.config.logo = false;

    const { ticket } = renderSaleDetailsReceipt(store, baseSaleDetails);

    expectSaleDetailsTicket(ticket, {
        logo: false,
        is_sold_section: true,
        total_paid: "150.00",
    });
});

test("sale details ticket renders no sold section when no products", async () => {
    const store = await setupPosEnv();

    const details = {
        ...baseSaleDetails,
        products: [],
    };

    const { ticket } = renderSaleDetailsReceipt(store, details);

    expectSaleDetailsTicket(ticket, {
        is_sold_section: false,
        is_refund_section: false,
        payments: [{ name: "Cash" }, { name: "Bank" }],
        total_paid: "150.00",
        is_company_info: true,
    });
});

test("sale details ticket renders multiple categories", async () => {
    const store = await setupPosEnv();

    const details = {
        currency: { total_paid: 250 },
        products: [
            {
                name: "Food",
                qty: 3,
                total: 150,
                products: [{ product_id: 1, product_name: "Burger", quantity: 3, total_paid: 150 }],
            },
            {
                name: "Drinks",
                qty: 4,
                total: 100,
                products: [
                    { product_id: 2, product_name: "Cola", quantity: 2, total_paid: 50 },
                    { product_id: 3, product_name: "Water", quantity: 2, total_paid: 50 },
                ],
            },
        ],
        refund_products: [],
        cancelled_products: [],
        payments: [{ name: "Cash", total: 250 }],
        taxes: [],
    };

    const { ticket } = renderSaleDetailsReceipt(store, details);

    expectSaleDetailsTicket(ticket, {
        is_sold_section: true,
        sold_categories: [
            { name: "Food", products: ["Burger"] },
            { name: "Drinks", products: ["Cola", "Water"] },
        ],
        total_paid: "250.00",
    });
});
