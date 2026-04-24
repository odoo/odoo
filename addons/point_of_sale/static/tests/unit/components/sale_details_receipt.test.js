import { test, expect } from "@odoo/hoot";
import { renderToElement } from "@web/core/utils/render";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

const normalizeText = (value = "") => value.replace(/\s+/g, " ").trim();

const renderSaleDetailsReceipt = (store, saleDetails) => {
    const generator = store.ticketPrinter.getGenerator({ models: store.models });
    const data = generator.generateSaleDetailsData(saleDetails);
    const ticket = renderToElement("point_of_sale.pos_sale_details_receipt", data);
    return { data, ticket };
};

const expectSaleDetailsTicket = (ticket, expected) => {
    if (expected.logo) {
        const logo = ticket.querySelector("div[name='logo'] img");
        expect(Boolean(logo)).toBe(true, {
            message: "Ticket should have a logo image",
        });
    } else if (expected.logo === false) {
        const logo = ticket.querySelector("div[name='logo'] img");
        expect(Boolean(logo)).toBe(false, {
            message: "Ticket should not have a logo image",
        });
    }

    if (expected.is_sold_section) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const soldHeader = headers.find((h) => normalizeText(h.textContent) === "SOLD:");
        expect(Boolean(soldHeader)).toBe(true, {
            message: "Ticket should have SOLD: section header",
        });
    } else if (expected.is_sold_section === false) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const soldHeader = headers.find((h) => normalizeText(h.textContent) === "SOLD:");
        expect(Boolean(soldHeader)).toBe(false, {
            message: "Ticket should not have SOLD: section header",
        });
    }

    if (expected.sold_categories) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const soldIdx = headers.findIndex((h) => normalizeText(h.textContent) === "SOLD:");
        expect(soldIdx).toBeGreaterThan(-1);
        for (const cat of expected.sold_categories) {
            expect(normalizeText(ticket.textContent)).toInclude(cat.name);
            if (cat.products) {
                for (const product of cat.products) {
                    expect(normalizeText(ticket.textContent)).toInclude(product);
                }
            }
        }
    }

    if (expected.is_refund_section) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const refundHeader = headers.find((h) => normalizeText(h.textContent) === "REFUNDED:");
        expect(Boolean(refundHeader)).toBe(true, {
            message: "Ticket should have REFUNDED: section header",
        });
    } else if (expected.is_refund_section === false) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const refundHeader = headers.find((h) => normalizeText(h.textContent) === "REFUNDED:");
        expect(Boolean(refundHeader)).toBe(false, {
            message: "Ticket should not have REFUNDED: section header",
        });
    }

    if (expected.payments) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const paymentsHeader = headers.find((h) => normalizeText(h.textContent) === "PAYMENTS:");
        expect(Boolean(paymentsHeader)).toBe(true, {
            message: "Ticket should have PAYMENTS: section header",
        });
        for (const payment of expected.payments) {
            expect(normalizeText(ticket.textContent)).toInclude(payment.name);
            if (payment.total) {
                expect(normalizeText(ticket.textContent)).toInclude(payment.total);
            }
        }
    }

    if (expected.taxes) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const taxesHeader = headers.find((h) => normalizeText(h.textContent) === "TAXES:");
        expect(Boolean(taxesHeader)).toBe(true, {
            message: "Ticket should have TAXES: section header",
        });
        for (const tax of expected.taxes) {
            expect(normalizeText(ticket.textContent)).toInclude(tax.name);
        }
    }

    if (expected.total_paid) {
        const headers = [...ticket.querySelectorAll(".text-large.text-center.text-bold")];
        const totalHeader = headers.find((h) => normalizeText(h.textContent) === "TOTAL:");
        expect(Boolean(totalHeader)).toBe(true, {
            message: "Ticket should have TOTAL: section header",
        });
        expect(normalizeText(ticket.textContent)).toInclude("Total paid");
        expect(normalizeText(ticket.textContent)).toInclude(expected.total_paid);
    }

    if (expected.is_company_info) {
        const companyInfo = ticket.querySelector("tbody[name='company_info']");
        expect(Boolean(companyInfo)).toBe(true, {
            message: "Ticket should have company info section",
        });
    } else if (expected.is_company_info === false) {
        expect(Boolean(ticket.querySelector("tbody[name='company_info']"))).toBe(false, {
            message: "Ticket should not have company info section",
        });
    }
};

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
