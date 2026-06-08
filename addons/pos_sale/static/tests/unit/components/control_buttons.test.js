import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import "@pos_sale/app/components/screens/product_screen/control_buttons/control_buttons";

definePosModels();

test("PosOrderDoesNotRemainInList / test_ecommerce_paid_order_is_hidden_in_pos / test_ecommerce_unpaid_order_is_shown_in_pos: onClickQuotation filters sale orders by unpaid amount and POS currency", async () => {
    const store = await setupPosEnv();
    const dialogs = [];
    store.addNewOrder();
    store.dialog.add = (component, props) => dialogs.push({ component, props });

    const component = await mountWithCleanup(ControlButtons, {});
    component.onClickQuotation();

    expect(dialogs).toHaveLength(1);
    expect(dialogs[0].props.context).toEqual({});
    expect(dialogs[0].props.domain).toEqual([
        ["state", "!=", "cancel"],
        ["invoice_status", "!=", "invoiced"],
        ["currency_id", "=", store.currency.id],
        ["amount_unpaid", ">", 0],
    ]);
});

test("PosSettleOrder: onClickQuotation adds selected partner filters to the dialog", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    store.addNewOrder({ partner_id: partner });

    const dialogs = [];
    store.dialog.add = (component, props) => dialogs.push({ component, props });

    const component = await mountWithCleanup(ControlButtons, {});
    component.onClickQuotation();

    expect(dialogs).toHaveLength(1);
    expect(dialogs[0].props.context).toEqual({
        search_default_partner_id: partner.id,
    });
    expect(dialogs[0].props.domain).toEqual([
        ["state", "!=", "cancel"],
        ["invoice_status", "!=", "invoiced"],
        ["currency_id", "=", store.currency.id],
        ["amount_unpaid", ">", 0],
        ["partner_id", "any", [["id", "child_of", [partner.id]]]],
    ]);
});

test("PosSettleOrder: onClickQuotation forwards the selected sale order id to the POS store", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const selectedIds = [];
    store.onClickSaleOrder = async (id) => selectedIds.push(id);

    const dialogs = [];
    store.dialog.add = (component, props) => dialogs.push({ component, props });

    const component = await mountWithCleanup(ControlButtons, {});
    component.onClickQuotation();

    expect(dialogs).toHaveLength(1);
    await dialogs[0].props.onSelected([42]);
    expect(selectedIds).toEqual([42]);
});
