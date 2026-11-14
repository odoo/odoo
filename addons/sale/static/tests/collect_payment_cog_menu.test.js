import { expect, test } from "@odoo/hoot";
import { contains, mountView, onRpc, toggleActionMenu } from "@web/../tests/web_test_helpers";

import { defineSaleModels } from "./sale_test_helpers";
import { SaleOrder } from "./mock_server/mock_models/sale_order";

defineSaleModels();

test("mark as paid is hidden from users without invoicing rights", async () => {
    SaleOrder._records = [{ id: 1, name: "S00001", state: "sale" }];
    onRpc("has_group", () => false);
    await mountView({
        type: "form",
        resModel: "sale.order",
        resId: 1,
        actionMenus: {},
        arch: `<form><field name="name"/><field name="state"/></form>`,
    });
    await toggleActionMenu();
    await contains("button.o-dropdown:contains(Collect Payment)").click();

    expect(".o_menu_item:contains(Mark as Paid)").toHaveCount(0);
});
