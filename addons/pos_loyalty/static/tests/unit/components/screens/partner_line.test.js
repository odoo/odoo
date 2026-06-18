import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("getLoyaltyPoints lists loyalty balances for the partner", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    // Fresh order with no partner: getLoyaltyPoints reads each program's card balance.
    store.addNewOrder();

    // Partner 1 holds card 1 (program 1, 10 pts) and card 4 (program 7, 3 pts).
    const partner = models["res.partner"].get(1);

    const component = await mountWithCleanup(PartnerLine, {
        props: {
            partner,
            close: () => {},
            isSelected: false,
            isBalanceDisplayed: true,
            onClickEdit: () => {},
            onClickUnselect: () => {},
            onClickPartner: () => {},
            onClickOrders: () => {},
        },
    });

    const entries = component.getLoyaltyPoints();
    const byProgram = Object.fromEntries(entries.map((e) => [e.id, e.repr]));

    expect(byProgram[1]).toBe("10.00 Points");
    expect(byProgram[7]).toBe("3.00 Points");
    // eWallet balances are listed as currency; gift_card programs are not listed.
    expect(byProgram[2]).toMatch(/E-Wallet Program: .*25\.00/);
    const ids = entries.map((e) => e.id);
    expect(ids).not.toInclude(3);
});
