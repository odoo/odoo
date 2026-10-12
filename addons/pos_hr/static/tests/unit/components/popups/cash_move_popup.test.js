import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { CashMovePopup } from "@point_of_sale/app/components/popups/cash_move_popup/cash_move_popup";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("_getCashInOutExtraParams", async () => {
    await setupPosEnv();
    const comp = await mountWithCleanup(CashMovePopup, {
        props: { close: () => {} },
    });
    const res = comp._getCashInOutExtraParams();
    expect(res.employee_id).toBe(2);
});
test("partnerId", async () => {
    const store = await setupPosEnv();
    const comp = await mountWithCleanup(CashMovePopup, {
        props: { close: () => {} },
    });
    const emp = store.models["hr.employee"].get(2);
    store.setCashier(emp);
    expect(comp.partnerId).toBe(emp.work_contact_id.id);
});
test("handleAmountBlur", async () => {
    await setupPosEnv();
    const comp = await mountWithCleanup(CashMovePopup, {
        props: { close: () => {} },
    });
    comp.state.amount = "10";
    comp.handleAmountBlur();
    expect(comp.state.amount).toBe("10.00");
});
