import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { ProductConfiguratorPopup } from "@point_of_sale/app/components/popups/product_configurator_popup/product_configurator_popup";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("Include extra price for dynamic variants in popup", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(60);
    productTemplate.product_variant_ids = [];
    store.models["product.template.attribute.value"].get(8).price_extra = 10;;
    store.models["product.template.attribute.value"].get(10).price_extra = 20;

    const popup = await mountWithCleanup(ProductConfiguratorPopup, {
        props: {
            productTemplate: productTemplate,
            getPayload: () => {},
            close: () => {},
        },
    });
    expect(popup.priceExtra).toBe(30);
    expect(popup.title.includes("50")).toBe(true);
});
