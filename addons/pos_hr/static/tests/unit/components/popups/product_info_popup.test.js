import { test, expect } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("allowProductEdition", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const admin = store.models["hr.employee"].get(2);
    store.setCashier(admin);
    const product = store.models["product.template"].get(5);
    const info = await store.getProductInfo(product, 1);
    const comp = await mountWithCleanup(ProductInfoPopup, {
        props: {
            productTemplate: product,
            info,
            close: () => {},
        },
    });
    expect(comp.allowProductEdition).toBe(true);
    const emp = store.models["hr.employee"].get(3);
    store.setCashier(emp);
    expect(comp.allowProductEdition).toBe(false);
});

test("financials for minimal employee", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const info = await store.getProductInfo(product, 1);
    await mountWithCleanup(ProductInfoPopup, {
        props: {
            productTemplate: product,
            info,
            close: () => {},
        },
    });

    const admin = store.models["hr.employee"].get(2);
    store.setCashier(admin);
    expect(".financials-order").toHaveCount(1);

    const minimalEmployee = store.models["hr.employee"].get(4);
    store.setCashier(minimalEmployee);
    await animationFrame();
    expect(".financials-order").toHaveCount(0);
});
