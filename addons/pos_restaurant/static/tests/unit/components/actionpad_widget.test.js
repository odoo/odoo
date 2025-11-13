import { expect, test } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("highlightPay", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const comp = await mountWithCleanup(ActionpadWidget, {
        props: {
            actionName: "Payment",
            actionToTrigger: () => {},
        },
    });

    expect(comp.highlightPay).toBe(false);
    // simulating order send
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);

    // orderline qty change
    order.lines[1].qty = 21;
    expect(comp.highlightPay).toBe(false);
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);

    // orderline note update
    order.lines[0].note = "Test Orderline Note";
    expect(comp.highlightPay).toBe(false);
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);

    // general customer note
    order.general_customer_note = "Test Order Customer Note";
    expect(comp.highlightPay).toBe(false);
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);

    // internal note
    order.internal_note = "Test Order Internal Note";
    expect(comp.highlightPay).toBe(false);
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);
});
