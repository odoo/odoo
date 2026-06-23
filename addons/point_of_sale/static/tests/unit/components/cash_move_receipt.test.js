import { test, expect } from "@odoo/hoot";
import { renderToElement } from "@web/core/utils/render";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

const normalizeText = (value = "") => value.replace(/\s+/g, " ").trim();

const renderCashMoveReceipt = (store, { reason, translatedType, formattedAmount }) => {
    const order = store.addNewOrder();
    const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
    const data = generator.generateCashMoveData({ reason, translatedType, formattedAmount });
    const ticket = renderToElement("point_of_sale.pos_cash_move_receipt", data);
    return { data, ticket };
};

const expectCashMoveTicket = (ticket, expected) => {
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

    if (expected.type) {
        const typeEl = [...ticket.querySelectorAll(".text-center.text-large")].find((el) =>
            normalizeText(el.textContent).includes("CASH")
        );
        expect(Boolean(typeEl)).toBe(true, {
            message: "Ticket should have CASH type element",
        });
        expect(normalizeText(typeEl.textContent)).toInclude(expected.type);
    }

    if (expected.amount) {
        const rows = [...ticket.querySelectorAll("table tbody tr")];
        const amountRow = rows.find((r) => normalizeText(r.textContent).includes("AMOUNT"));
        expect(Boolean(amountRow)).toBe(true, {
            message: "Ticket should have AMOUNT row",
        });
        expect(normalizeText(amountRow.textContent)).toInclude(expected.amount);
    }

    if (expected.reason) {
        const rows = [...ticket.querySelectorAll("table tbody tr")];
        const reasonRow = rows.find((r) => normalizeText(r.textContent).includes("REASON"));
        expect(Boolean(reasonRow)).toBe(true, {
            message: "Ticket should have REASON row",
        });
        expect(normalizeText(reasonRow.textContent)).toInclude(expected.reason);
    }

    if (expected.date) {
        const dateEl = ticket.querySelector(".text-large.text-center");
        expect(Boolean(dateEl)).toBe(true, {
            message: "Ticket should have date element",
        });
        expect(normalizeText(dateEl.textContent)).toInclude(expected.date);
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

test("cash move ticket renders cash in with amount and reason", async () => {
    const store = await setupPosEnv();

    const { ticket } = renderCashMoveReceipt(store, {
        reason: "Starting float",
        translatedType: "in",
        formattedAmount: "$ 100.00",
    });

    expectCashMoveTicket(ticket, {
        type: "CASH IN",
        amount: "$ 100.00",
        reason: "Starting float",
        is_company_info: true,
    });
});

test("cash move ticket renders cash out with amount and reason", async () => {
    const store = await setupPosEnv();

    const { ticket } = renderCashMoveReceipt(store, {
        reason: "Supplier payment",
        translatedType: "out",
        formattedAmount: "$ 50.00",
    });

    expectCashMoveTicket(ticket, {
        type: "CASH OUT",
        amount: "$ 50.00",
        reason: "Supplier payment",
        is_company_info: true,
    });
});

test("cash move ticket renders logo when configured", async () => {
    const store = await setupPosEnv();
    store.config.logo =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z9DwHwAGBQKA3H7sNwAAAABJRU5ErkJggg==";

    const { ticket } = renderCashMoveReceipt(store, {
        reason: "Test",
        translatedType: "in",
        formattedAmount: "$ 10.00",
    });

    expectCashMoveTicket(ticket, {
        logo: true,
        type: "CASH IN",
        amount: "$ 10.00",
        reason: "Test",
    });
});

test("cash move ticket does not render logo when not configured", async () => {
    const store = await setupPosEnv();
    store.config.logo = false;

    const { ticket } = renderCashMoveReceipt(store, {
        reason: "Test",
        translatedType: "out",
        formattedAmount: "$ 25.00",
    });

    expectCashMoveTicket(ticket, {
        logo: false,
        type: "CASH OUT",
        amount: "$ 25.00",
        reason: "Test",
    });
});

test("cash move ticket renders different amounts correctly", async () => {
    const store = await setupPosEnv();

    const cases = [
        { reason: "Petty cash", type: "in", amount: "$ 200.00" },
        { reason: "Change refill", type: "in", amount: "$ 500.00" },
        { reason: "Bank deposit", type: "out", amount: "$ 1,000.00" },
    ];

    for (const c of cases) {
        const { ticket } = renderCashMoveReceipt(store, {
            reason: c.reason,
            translatedType: c.type,
            formattedAmount: c.amount,
        });

        expectCashMoveTicket(ticket, {
            type: `CASH ${c.type.toUpperCase()}`,
            amount: c.amount,
            reason: c.reason,
        });
    }
});
