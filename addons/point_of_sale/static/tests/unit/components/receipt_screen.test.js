import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

definePosModels();

test("Total on receipt always incl", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.config.iface_tax_included = "total";
    await mountWithCleanup(ReceiptScreen, {
        props: { orderUuid: order.uuid },
    });
    const total = queryOne(".pos-receipt-amount .pos-receipt-right-align");
    expect(total.innerHTML).toBe("$&nbsp;17.85");
    order.config.iface_tax_included = "subtotal";
    const subtotal = queryOne(".pos-receipt-amount .pos-receipt-right-align");
    expect(subtotal.innerHTML).toBe("$&nbsp;17.85");
});
