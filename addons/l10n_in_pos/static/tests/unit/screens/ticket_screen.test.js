import { expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, makeOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

definePosModels();

test("search by B2C invoice number in the invoice number field", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    makeOrder(store, { pos_reference: "O-01", l10n_in_b2c_invoice_number: "P26/01/000000001" });
    makeOrder(store, { pos_reference: "O-02", l10n_in_b2c_invoice_number: "P26/01/000000002" });
    makeOrder(store, { pos_reference: "O-03" });
    screen.state.filter = "ACTIVE_ORDERS";
    screen.state.search = { fieldName: "INVOICE_NUMBER", searchTerm: "000000002" };

    expect(screen._computeSyncedOrdersDomain()).toEqual([
        ["account_move.name", "ilike", "%000000002%"],
    ]);

    store.company.country_id.code = "IN";

    // Orders of the session are filtered locally.
    const result = screen.getFilteredOrderList();
    expect(result.length).toBe(1);
    expect(result[0].pos_reference).toBe("O-02");

    // Paid orders are searched on the server.
    expect(screen._computeSyncedOrdersDomain()).toEqual([
        "|",
        ["l10n_in_b2c_invoice_number", "ilike", "%000000002%"],
        ["account_move.name", "ilike", "%000000002%"],
    ]);
});
