import { test, expect } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("_getProductByBarcode", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const comp = await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
    await comp.addProductToOrder(store.models["product.template"].get(5));

    expect(order.displayPrice).toBe(3.45);
    expect(comp.total).toBe("$\u00a03.45");
    expect(comp.items).toBe("1");

    const productByBarcode = await comp._getProductByBarcode({ base_code: "test_test" });
    expect(productByBarcode.id).toEqual(5);
});

test("fastValidate", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const order = store.getOrder();
    const fastPaymentMethod = order.config.fast_payment_method_ids[0];
    const productScreen = await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });
    await productScreen.addProductToOrder(store.models["product.template"].get(5));

    expect(order.displayPrice).toBe(3.45);
    expect(productScreen.total).toBe("$\u00a03.45");
    expect(productScreen.items).toBe("1");

    await productScreen.fastValidate(fastPaymentMethod);

    expect(order.payment_ids[0].payment_method_id).toEqual(fastPaymentMethod);
    expect(order.state).toBe("paid");
    expect(order.amount_paid).toBe(3.45);
});

test("full slots remain available in POS", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const preset = store.models["pos.preset"].get(2);
    preset.slots_per_interval = 1;

    await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
    store.selectPreset(preset);
    await contains(".o_dialog .btn:contains('03/12/2019')").click();

    const fullSlots = queryAll(".preset-slot-button.o_colorlist_item_numpad_color_1");
    const fullSlot = preset.availabilities["2019-03-12"].find(
        (s) => s.time === "2019-03-12 12:00:00"
    );
    expect(fullSlot.isFull).toBe(true);
    expect(fullSlots[0].textContent.trim()).toBe("12:00");
});
