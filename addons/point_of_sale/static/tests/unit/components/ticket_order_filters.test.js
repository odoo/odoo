import { test, expect, mockDate } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { formatDate, serializeDateTime } from "@web/core/l10n/dates";
import { setupPosEnv, makeOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

const STATUSES = ["ACTIVE_ORDERS", "ONGOING", "PAYMENT", "OPEN", "TIPPING", "SYNCED", "CANCELLED"];

const filterValues = (overrides = {}) => ({
    status: "SYNCED",
    searchFieldName: "REFERENCE",
    searchTerm: "",
    partnerId: null,
    presetId: null,
    ...overrides,
});

/** The order as stored on the server, for `Domain.contains`. */
const toServerOrder = (order, { partnerById = false } = {}) => ({
    state: order.state,
    tracking_number: order.tracking_number,
    floating_order_name: order.floating_order_name || false,
    pos_reference: order.pos_reference,
    date_order: serializeDateTime(order.date_order),
    partner_id: partnerById
        ? order.partner_id?.id || false
        : { complete_name: order.partner_id?.name || false },
    preset_id: order.preset_id?.id || false,
});

test("active orders are split by screen; paid and cancelled orders have their own status", async () => {
    const store = await setupPosEnv();
    const { filters } = await mountWithCleanup(TicketScreen);
    const onScreen = (name, state = "draft") =>
        makeOrder(store, { state, getScreenData: () => ({ name }) });
    const statusesOf = (order) => STATUSES.filter((status) => filters.matchesStatus(order, status));

    const ongoing = onScreen("ProductScreen");
    const payment = onScreen("PaymentScreen");
    const tipping = onScreen("TipScreen", "paid");
    const paid = onScreen("", "paid");
    const cancelled = onScreen("", "cancel");

    store.config.set_tip_after_payment = false;
    expect(statusesOf(ongoing)).toEqual(["ACTIVE_ORDERS", "ONGOING"]);
    expect(statusesOf(payment)).toEqual(["ACTIVE_ORDERS", "PAYMENT"]);
    expect(statusesOf(paid)).toEqual(["SYNCED"]);
    expect(statusesOf(cancelled)).toEqual(["CANCELLED"]);

    store.config.set_tip_after_payment = true;
    expect(statusesOf(payment)).toEqual(["ACTIVE_ORDERS", "OPEN"]);
    expect(statusesOf(tipping)).toEqual(["ACTIVE_ORDERS", "TIPPING", "SYNCED"], {
        message: "a paid order waiting for its tip stays active",
    });
});

test("each filter selects the same orders in memory and on the server", async () => {
    mockDate("2026-05-15 12:00:00", 0);
    const store = await setupPosEnv();
    const { filters } = await mountWithCleanup(TicketScreen);
    const [preset, otherPreset] = store.models["pos.preset"].getAll();
    const [partner, otherPartner] = store.models["res.partner"].filter((p) => p.name);
    const now = DateTime.now();
    const yesterday = now.minus({ days: 1 });

    const paidToday = makeOrder(store, {
        state: "paid",
        tracking_number: "T-42",
        pos_reference: "R-001",
        date_order: now,
        partner_id: partner,
        preset_id: preset,
    });
    const paidYesterday = makeOrder(store, {
        state: "paid",
        tracking_number: "T-7",
        pos_reference: "R-002",
        date_order: yesterday,
        partner_id: otherPartner,
        preset_id: otherPreset,
    });
    const cancelled = makeOrder(store, {
        state: "cancel",
        tracking_number: "T-43",
        pos_reference: "R-003",
        date_order: now,
        partner_id: partner,
        preset_id: preset,
    });
    const orders = [paidToday, paidYesterday, cancelled];

    const cases = [
        [{}, [paidToday, paidYesterday]],
        [{ status: "CANCELLED" }, [cancelled]],
        // Trimmed, case-insensitive, on the tracking number.
        [{ searchFieldName: "REFERENCE", searchTerm: " t-4 " }, [paidToday]],
        [{ searchFieldName: "RECEIPT_NUMBER", searchTerm: "r-002" }, [paidYesterday]],
        [{ searchFieldName: "DATE", searchTerm: "Tod" }, [paidToday]],
        [{ searchFieldName: "DATE", searchTerm: formatDate(yesterday) }, [paidYesterday]],
        [{ searchFieldName: "PARTNER", searchTerm: otherPartner.name }, [paidYesterday]],
        [{ presetId: preset.id }, [paidToday]],
        // The partner picked replaces the search term.
        [
            { searchFieldName: "PARTNER", searchTerm: "nobody", partnerId: partner.id },
            [paidToday],
            { partnerById: true },
        ],
    ];
    for (const [overrides, expected, serverOptions] of cases) {
        const values = filterValues(overrides);
        const domain = filters.toDomain(values);
        const message = JSON.stringify(overrides);
        expect(orders.filter((order) => filters.matches(order, values))).toEqual(expected, {
            message,
        });
        expect(
            orders.filter((order) => domain.contains(toServerOrder(order, serverOptions)))
        ).toEqual(expected, { message: `${message} (server)` });
    }
});
