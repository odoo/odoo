import { test, expect, mockUserAgent } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";

definePosModels();

const addVivaMethod = (store) => {
    const viva = store.models["pos.payment.method"].create({
        id: 1201,
        name: "Viva",
        payment_provider: "viva_com",
        payment_method_type: "terminal",
        type: "bank",
    });
    viva.payment_interface = new PaymentInterface(store, viva);
    store.config.payment_method_ids = [...store.config.payment_method_ids, viva];
    store.paymentMethods.initDefaults();
    return viva;
};

test("a single viva method is grouped on android, with the viva app option", async () => {
    mockUserAgent("android");
    const store = await setupPosEnv();
    const plugin = store.paymentMethods;
    const viva = addVivaMethod(store);

    expect(plugin.defaultGroups.viva_com).toEqual([viva]);
    expect(plugin.getProviderOptions("viva_com")).toEqual([
        { name: "use_app", label: "Use the Viva app installed on this device", value: false },
    ]);

    plugin.setProviderOptions("viva_com", { use_app: true });
    expect(window.localStorage.getItem("vivawallet_app_answer")).toBe("true");
    expect(plugin.getProviderOptions("viva_com")[0].value).toBe(true);

    plugin.setProviderOptions("viva_com", { use_app: false });
    expect(window.localStorage.getItem("vivawallet_app_answer")).toBe("false");
});

test("a single viva method is not grouped outside android", async () => {
    const store = await setupPosEnv();
    addVivaMethod(store);
    expect(store.paymentMethods.defaultGroups).toEqual({});
    expect(store.paymentMethods.getProviderOptions("viva_com")).toEqual([]);
});
