import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("getDisplayPriceWithQty", async () => {
    const store = await setupSelfPosEnv();
    const order = await getFilledSelfOrder(store);
    const [line1, line2] = order.lines;

    store.config.iface_tax_included = "subtotal";
    expect(line1.getDisplayPriceWithQty(3)).toBe(300);
    expect(line2.getDisplayPriceWithQty(2)).toBe(200);

    store.config.iface_tax_included = "total";
    expect(line1.getDisplayPriceWithQty(3)).toBe(345);
    expect(line2.getDisplayPriceWithQty(2)).toBe(250);
});
