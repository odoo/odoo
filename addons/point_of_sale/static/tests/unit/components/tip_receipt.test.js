import { test, expect } from "@odoo/hoot";
import { renderToElement } from "@web/core/utils/render";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

const normalizeText = (value = "") => value.replace(/\s+/g, " ").trim();

const renderTipReceipt = (store, order, name = "") => {
    const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
    const data = generator.generateTipData(name);
    const ticket = renderToElement("point_of_sale.pos_tip_receipt", data);
    return { data, ticket };
};

const expectTipTicket = (ticket, expected) => {
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

    if (expected.title) {
        const titleEl = ticket.querySelector(".text-large.text-center.text-bold");
        expect(Boolean(titleEl)).toBe(true, {
            message: "Ticket should have a title element",
        });
        expect(normalizeText(titleEl.textContent)).toInclude(expected.title);
    }

    if (expected.name) {
        const nameEl = ticket.querySelector(".pos-payment-terminal-receipt");
        expect(Boolean(nameEl)).toBe(true, {
            message: "Ticket should have a name/terminal receipt element",
        });
        expect(normalizeText(nameEl.textContent)).toInclude(expected.name);
    } else if (expected.name === false) {
        expect(Boolean(ticket.querySelector(".pos-payment-terminal-receipt"))).toBe(false, {
            message: "Ticket should not have a name element when name is empty",
        });
    }

    if (expected.subtotal_amount) {
        const subtotalRow = ticket.querySelector("td[name='subtotal']");
        expect(Boolean(subtotalRow)).toBe(true, {
            message: "Ticket should have subtotal row",
        });
        const subtotalValue = subtotalRow.parentElement.querySelector("td:last-child");
        expect(normalizeText(subtotalValue.textContent)).toInclude(expected.subtotal_amount);
    }

    if (expected.total_amount) {
        const totalEl = ticket.querySelector(".total-amount");
        expect(Boolean(totalEl)).toBe(true, {
            message: "Ticket should have total-amount element",
        });
        expect(normalizeText(totalEl.textContent)).toInclude(expected.total_amount);
    }

    if (expected.is_tip_line) {
        const tables = [...ticket.querySelectorAll("table.mb-3")];
        const tipTable = tables.find((t) => normalizeText(t.textContent).includes("Tip:"));
        expect(Boolean(tipTable)).toBe(true, {
            message: "Ticket should have Tip line with blank space",
        });
    }

    if (expected.is_signature_line) {
        const tables = [...ticket.querySelectorAll("table.mb-3")];
        const sigTable = tables.find((t) => normalizeText(t.textContent).includes("Signature:"));
        expect(Boolean(sigTable)).toBe(true, {
            message: "Ticket should have Signature line",
        });
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

test("tip ticket renders title, totals, tip and signature lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 2 }, order);
    line.setUnitPrice(10);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order);

    expectTipTicket(ticket, {
        title: "Tip Receipt",
        total_amount: "20.00",
        subtotal_amount: "20.00",
        is_tip_line: true,
        is_signature_line: true,
        is_company_info: true,
    });
});

test("tip ticket renders customer name when provided", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setUnitPrice(15);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order, "John Doe");

    expectTipTicket(ticket, {
        title: "Tip Receipt",
        name: "John Doe",
        total_amount: "15.00",
    });
});

test("tip ticket does not render name element when name is empty", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setUnitPrice(5);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order, "");

    expectTipTicket(ticket, {
        title: "Tip Receipt",
        name: false,
        total_amount: "5.00",
    });
});

test("tip ticket renders logo when configured", async () => {
    const store = await setupPosEnv();
    store.config.logo =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==";
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setUnitPrice(10);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order);

    expectTipTicket(ticket, {
        logo: true,
        title: "Tip Receipt",
        total_amount: "10.00",
    });
});

test("tip ticket does not render logo when not configured", async () => {
    const store = await setupPosEnv();
    store.config.logo = false;
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
    line.setUnitPrice(10);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order);

    expectTipTicket(ticket, {
        logo: false,
        title: "Tip Receipt",
        total_amount: "10.00",
    });
});

test("tip ticket renders correct total for multiple quantities", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);

    const line = await store.addLineToOrder({ product_tmpl_id: product, qty: 4 }, order);
    line.setUnitPrice(25);
    line.price_type = "manual";
    line.tax_ids = [];
    order.setOrderPrices();

    const { ticket } = renderTipReceipt(store, order);

    expectTipTicket(ticket, {
        title: "Tip Receipt",
        total_amount: "100.00",
        subtotal_amount: "100.00",
        is_tip_line: true,
        is_signature_line: true,
        is_company_info: true,
    });
});
