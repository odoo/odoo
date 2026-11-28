import { test, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { createTestProduct, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { setupPoSEnvForSelfOrder } from "../../utils";

definePosModels();

test("the delivery line of a self-order is left out of the service fee base in the POS", async () => {
    const store = await setupPoSEnvForSelfOrder();
    const { template: deliveryTemplate, variant: deliveryProduct } = createTestProduct(store, {
        name: "Delivery",
        price: 5,
    });
    const preset = store.models["pos.preset"].get(24);
    preset.delivery_product_id = deliveryProduct;
    const order = await getFilledOrder(store);
    order.preset_id = preset;
    await store.addLineToOrder({ product_tmpl_id: deliveryTemplate, qty: 1 }, order);

    const deliveryLine = order.lines.find((l) => l.product_id.id === deliveryProduct.id);
    const productLine = order.lines.find((l) => l !== deliveryLine);
    expect(deliveryLine.isDeliveryLine).toBe(true);
    expect(deliveryLine.isServiceFeeApplicable()).toBe(false);
    expect(productLine.isDeliveryLine).toBe(false);
    expect(productLine.isServiceFeeApplicable()).toBe(true);
});
