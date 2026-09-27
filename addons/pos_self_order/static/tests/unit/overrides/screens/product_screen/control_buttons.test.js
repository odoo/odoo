import { expect, describe, test } from "@odoo/hoot";
import { mountWithCleanup, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPoSEnvForSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";

definePosModels();

describe("clickDynamicQr", () => {
    test("opens no popup and warns when the server returns no url", async () => {
        const store = await setupPoSEnvForSelfOrder();
        store.addNewOrder();
        onRpc("pos.config", "get_dynamic_qr_url", () => false);
        const comp = await mountWithCleanup(ControlButtons, { props: {} });

        let notified = null;
        patchWithCleanup(comp.notification, {
            add(message, options) {
                notified = { message, options };
            },
        });
        let dialogOpened = false;
        patchWithCleanup(comp.dialog, {
            add() {
                dialogOpened = true;
            },
        });

        await comp.clickDynamicQr();

        expect(dialogOpened).toBe(false);

        expect(notified).toMatchObject({
            message: "Something went wrong while generating the QR code",
            options: { type: "danger" },
        });
    });

    test("syncs the order if needed, then opens the popup and updates the customer display", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const order = await getFilledOrder(store);
        onRpc("pos.config", "get_dynamic_qr_url", () => "http://example.com/pos-self/1/order/abc");
        const comp = await mountWithCleanup(ControlButtons, { props: {} });

        let dialogArgs = null;
        patchWithCleanup(comp.dialog, {
            add(component, props, options) {
                dialogArgs = { component, props, options };
            },
        });
        const customerDisplayQrCalls = [];
        patchWithCleanup(store, {
            updateCustomerDisplayQrData(qrCode, options) {
                customerDisplayQrCalls.push({ qrCode, options });
            },
        });

        expect(order.id).toBeOfType("string");
        await comp.clickDynamicQr();

        expect(order.id).toBeOfType("number");
        expect(dialogArgs.props).toMatchObject({
            url: "http://example.com/pos-self/1/order/abc",
            order,
        });
        expect(dialogArgs.props.qrCode).toInclude("data:image");
        expect(customerDisplayQrCalls).toHaveLength(1);
        expect(customerDisplayQrCalls[0]).toEqual({
            qrCode: dialogArgs.props.qrCode,
            options: { title: "Scan to join the order" },
        });

        dialogArgs.options.onClose();
        expect(customerDisplayQrCalls).toHaveLength(2);
        expect(customerDisplayQrCalls[1]).toEqual({ qrCode: null, options: undefined });
    });

    test("does not re-sync an already-saved order, even with newer unsynced edits", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const order = await getFilledOrder(store);
        await store.syncAllOrders({ orders: [order] });
        expect(order.id).toBeOfType("number");

        order.markDirty();
        expect(order.isDirty()).toBe(true);

        onRpc("pos.config", "get_dynamic_qr_url", () => "http://example.com/pos-self/1/order/abc");
        const comp = await mountWithCleanup(ControlButtons, { props: {} });

        let syncCalled = false;
        patchWithCleanup(store, {
            async syncAllOrders() {
                syncCalled = true;
            },
        });

        await comp.clickDynamicQr();

        expect(syncCalled).toBe(false);
    });
});
