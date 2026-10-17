import { expect, test } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "../data/generate_model_definitions";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

definePosStockModels();

async function mountProductScreen() {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    return { store, order, productScreen };
}

test("add product with expiration date", async () => {
    const { store, order, productScreen } = await mountProductScreen();
    const product = store.models["product.template"].get(27);
    const addProductPromise = productScreen.addProductToOrder(product);
    await contains(".lot-container input").edit("lot1", { confirm: false });
    await contains(".o-autocomplete--dropdown-item:contains(lot1)").click();
    const expirationDateSpan = document.querySelectorAll(".lot-item .form-control")[1];
    expect(expirationDateSpan.textContent.trim()).toBe("01/01/2027");
    await contains(".modal-footer .btn-primary").click();
    await addProductPromise;
    expect(order.lines[0].pack_lot_ids[0].lot_name).toBe("lot1");
    expect(order.lines[0].pack_lot_ids[0].expiration_date.toISODate()).toBe("2027-01-01");
});
