import { test } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { expectCashMoveTicket, renderCashMoveReceipt } from "../receipt_utils";

definePosModels();

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
