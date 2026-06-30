import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OptionalProductPage } from "@pos_self_order/app/pages/optional_product_page/optional_product_page";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { animationFrame, click } from "@odoo/hoot-dom";

definePosSelfModels();

test("optionalProducts and isOptionalProductSelected", async () => {
    const store = await setupSelfPosEnv();
    store.computeAvailableCategories();
    const models = store.models;
    const product = models["product.template"].get(5);
    product.update({ pos_optional_product_ids: [8, 10] });

    const comp = await mountWithCleanup(OptionalProductPage, {
        props: { productTemplate: product },
    });
    expect(comp.optionalProducts).toHaveLength(2);
    expect(Boolean(comp.showQtyButtons)).toBe(false);
    expect(comp.isOptionalProductSelected).toBe(false);

    await click("span:text('Wood chair')");
    await animationFrame();
    expect(comp.isOptionalProductSelected).toBe(true);
});
