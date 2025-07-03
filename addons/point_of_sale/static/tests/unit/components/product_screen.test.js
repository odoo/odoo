import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

test.tags("pos");
test("product_screen.js", async () => {
    const store = await setupPosEnv();
    const comp = await mountWithCleanup(ProductScreen, {});
    await comp.addProductToOrder(store.models["product.template"].get(5));
    const order = store.getOrder();

    expect(order.amount_total).toBe(3.45);
    expect(comp.total).toBe("$\u00a03.45");
    expect(comp.items).toBe("1");

    const productByBarcode = await comp._getProductByBarcode({ base_code: "test_test" });
    const match = store.models["product.product"].get(5);

    expect(productByBarcode).toEqual(match);
});
