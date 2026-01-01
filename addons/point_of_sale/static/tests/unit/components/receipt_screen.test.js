import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryFirst, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

definePosModels();

test("Total on receipt always incl", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.config.iface_tax_included = "total";
    await mountWithCleanup(ReceiptScreen, {
        props: { orderUuid: order.uuid },
    });
    let unitPrice = queryFirst(".info-list .price-per-unit");
    const total = queryOne(".pos-receipt-amount .pos-receipt-right-align");
    expect(unitPrice.innerHTML).toBe("$&nbsp;3.45 / Units");
    expect(total.innerHTML).toBe("$&nbsp;17.85");
    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    unitPrice = queryFirst(".info-list .price-per-unit");
    expect(unitPrice.innerHTML).toBe("$&nbsp;3.00 / Units");
    const subtotal = queryOne(".pos-receipt-amount .pos-receipt-right-align");
    expect(subtotal.innerHTML).toBe("$&nbsp;17.85");
});
