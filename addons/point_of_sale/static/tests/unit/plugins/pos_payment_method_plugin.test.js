import { test, expect } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";
import { setupPosEnv, addTestTerminals } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { SelectDefaultPaymentMethodPopup } from "@point_of_sale/app/components/popups/select_default_payment_method_popup/select_default_payment_method_popup";

definePosModels();

test("computeDefaultGroups", async () => {
    const store = await setupPosEnv();
    const plugin = store.paymentMethods;

    // Methods without payment interface are never grouped
    expect(plugin.defaultGroups).toEqual({});

    // A single method of a provider is not grouped
    const [terminal1] = addTestTerminals(store, 1);
    expect(plugin.defaultGroups).toEqual({});

    // Several methods of the same provider are grouped, by sequence
    const terminal2 = store.models["pos.payment.method"].create({
        id: 1102,
        name: "Test Terminal 2",
        payment_provider: "test_terminal",
        payment_method_type: "terminal",
        type: "bank",
        sequence: 5,
    });
    terminal2.payment_interface = new PaymentInterface(store, terminal2);
    store.config.payment_method_ids = [...store.config.payment_method_ids, terminal2];
    plugin.initDefaults();
    expect(Object.keys(plugin.defaultGroups)).toEqual(["test_terminal"]);
    expect(plugin.defaultGroups.test_terminal.map((pm) => pm.id)).toEqual([1102, terminal1.id]);
});

test("getDefault and setDefault", async () => {
    const store = await setupPosEnv();
    const plugin = store.paymentMethods;
    const [, terminal2] = addTestTerminals(store);
    const key = plugin.getDefaultStorageKey("test_terminal");

    expect(plugin.getDefault("test_terminal")).toBe(undefined);

    plugin.setDefault("test_terminal", terminal2.id);
    expect(plugin.getDefault("test_terminal")).toBe(terminal2);
    expect(localStorage.getItem(key)).toBe(String(terminal2.id));

    // The default is restored from the local storage
    plugin.defaultIds.test_terminal = false;
    plugin.initDefaults();
    expect(plugin.getDefault("test_terminal")).toBe(terminal2);

    // A stored method that is not part of the group is ignored
    localStorage.setItem(key, "9999");
    plugin.initDefaults();
    expect(plugin.getDefault("test_terminal")).toBe(undefined);

    plugin.setDefault("test_terminal", false);
    expect(plugin.getDefault("test_terminal")).toBe(undefined);
    expect(localStorage.getItem(key)).toBe(null);
});

test("selectDefaults", async () => {
    const store = await setupPosEnv();
    const plugin = store.paymentMethods;
    const [terminal1, terminal2] = addTestTerminals(store);
    plugin.setDefault("test_terminal", terminal1.id);

    let response;
    patch(plugin.dialog, {
        add(component, props, options) {
            expect(component).toBe(SelectDefaultPaymentMethodPopup);
            expect(props.groups).toHaveLength(1);
            const [group] = props.groups;
            expect(group.provider).toBe("test_terminal");
            expect(group.name).toBe("Test Provider");
            expect(group.paymentMethods.map((pm) => pm.id)).toEqual([terminal1.id, terminal2.id]);
            expect(group.selectedId).toBe(terminal1.id);
            if (response) {
                props.getPayload(response);
            } else {
                options.onClose();
            }
        },
    });

    // Cancelled: the default is kept
    response = null;
    expect(await plugin.selectDefaults()).toBe(false);
    expect(plugin.getDefault("test_terminal")).toBe(terminal1);

    // Confirmed: the default is updated
    response = { test_terminal: terminal2.id };
    expect(await plugin.selectDefaults()).toBe(true);
    expect(plugin.getDefault("test_terminal")).toBe(terminal2);
});
