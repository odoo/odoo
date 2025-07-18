import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder, patchSession } from "../utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();
beforeEach(patchSession);

describe("self_order - pos.order.line", () => {
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
});
