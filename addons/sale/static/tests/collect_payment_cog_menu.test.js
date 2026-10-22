import { expect, test } from "@odoo/hoot";
import {
    contains,
    mockService,
    mountView,
    onRpc,
    toggleActionMenu,
    toggleMenuItem,
} from "@web/../tests/web_test_helpers";

import { defineSaleModels } from "./sale_test_helpers";
import { SaleOrder } from "./mock_server/mock_models/sale_order";

defineSaleModels();

async function openCollectPayment({ isInvoicingUser }) {
    SaleOrder._records = [{ id: 1, name: "S00001", state: "sale" }];
    onRpc("has_group", () => isInvoicingUser);
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
        actionMenus: {},
        arch: `<form><field name="name"/><field name="state"/></form>`,
    });
    await toggleActionMenu();
    await contains("button.o-dropdown:contains(Collect Payment)").click();
}

test("mark as paid opens the payment of the order", async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step([params.name, params.resId]);
        },
    });
    await openCollectPayment({ isInvoicingUser: true });
    await toggleMenuItem("Mark as Paid");

    expect.verifySteps([["action_register_payment", 1]]);
});

test("mark as paid is hidden from users without invoicing rights", async () => {
    await openCollectPayment({ isInvoicingUser: false });

    expect(".o_menu_item:contains(Mark as Paid)").toHaveCount(0);
});
