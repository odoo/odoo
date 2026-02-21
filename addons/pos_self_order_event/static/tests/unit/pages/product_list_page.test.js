import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductListPage } from "@pos_self_order/app/pages/product_list_page/product_list_page";
import { setupSelfPosEnv } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";

definePosSelfModels();

test("selectProduct", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductListPage, {});

    comp.selectProduct(product);
    expect(store.currentOrder.lines).toHaveLength(1);
    expect(store.currentOrder.lines[0].product_id.id).toBe(5);

    // Event Product
    product._event_id = 1;
    comp.selectProduct(product);
    // Should not add event product to cart; should navigate to event page
    expect(store.currentOrder.lines).toHaveLength(1);
});
