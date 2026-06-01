import { describe, test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { makeWebrtcService } from "../webrtc/utils/webrtc_service";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { PeerDto } from "@point_of_sale/app/webrtc/webrtc_peer";

definePosModels();

test("dispatch", async () => {
    const webrtc = await makeWebrtcService();
    const pushMessageCalls = [];
    const debounceCalls = [];

    patchWithCleanup(webrtc, {
        pushMessage: (...args) => {
            pushMessageCalls.push(args);
        },
        debounceSendMessages: () => {
            debounceCalls.push(true);
        },
    });

    const adapter = new CustomerDisplayPosAdapter(webrtc);
    adapter.data = { finalized: true, amount: "$10" };

    adapter.dispatch();

    expect(pushMessageCalls).toEqual([
        [
            "update_customer_display",
            [{ finalized: true, amount: "$10" }],
            { group: "customer_display" },
        ],
    ]);
    expect(debounceCalls).toHaveLength(1);
});

describe("update_customer_display", () => {
    test("success", async () => {
        const webrtc = await makeWebrtcService({
            group: "terminal",
            deviceUuid: "test-uuid",
        });
        const adapter = new CustomerDisplayPosAdapter(webrtc);
        adapter.data = { finalized: true, amount: "$10" };

        const snapshot = webrtc._snapshotRegistry.get("update_customer_display");
        const target = new PeerDto("peer-1", "customer_display", "test-uuid");

        expect(snapshot.build(target)).toEqual({ finalized: true, amount: "$10" });
    });

    test("wrong device uuid", async () => {
        const webrtc = await makeWebrtcService({
            group: "terminal",
            deviceUuid: "test-uuid",
        });
        const adapter = new CustomerDisplayPosAdapter(webrtc);
        adapter.data = { finalized: true, amount: "$10" };

        const snapshot = webrtc._snapshotRegistry.get("update_customer_display");
        const target = new PeerDto("peer-1", "customer_display", "wrong-uuid");

        expect(snapshot.build(target)).toBe(null);
    });

    test("target not customer display", async () => {
        const webrtc = await makeWebrtcService({
            group: "terminal",
            deviceUuid: "test-uuid",
        });
        const adapter = new CustomerDisplayPosAdapter(webrtc);
        adapter.data = { finalized: true, amount: "$10" };

        const snapshot = webrtc._snapshotRegistry.get("update_customer_display");
        const target = new PeerDto("peer-1", "terminal", "test-uuid");

        expect(snapshot.build(target)).toBe(null);
    });

    test("webrtc not terminal", async () => {
        const webrtc = await makeWebrtcService({
            group: "customer_display",
            deviceUuid: "test-uuid",
        });
        const adapter = new CustomerDisplayPosAdapter(webrtc);
        adapter.data = { finalized: true, amount: "$10" };

        const snapshot = webrtc._snapshotRegistry.get("update_customer_display");
        const target = new PeerDto("peer-1", "customer_display", "test-uuid");

        expect(snapshot.build(target)).toBe(null);
    });
});

test("getOrderlineData", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const adapter = new CustomerDisplayPosAdapter({ registerSnapshot: () => {} });
    adapter.formatOrderData(order);

    expect(adapter.data.lines).toHaveLength(2);
    expect(adapter.data.lines[0].isSelected).toBe(false);
    expect(adapter.data.lines[1].isSelected).toBe(true);
});

test("order amounts summary", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const adapter = new CustomerDisplayPosAdapter({ registerSnapshot: () => {} });

    adapter.formatOrderData(order);
    expectFormattedPrice(adapter.data.amount, "$ 17.85");
    expectFormattedPrice(adapter.data.amountTaxes, "$ 2.85");
    expect(adapter.data.subtotal).toBe(false);

    store.config.iface_tax_included = "subtotal";
    adapter.formatOrderData(order);
    expectFormattedPrice(adapter.data.amount, "$ 17.85");
    expectFormattedPrice(adapter.data.amountTaxes, "$ 2.85");
    expectFormattedPrice(adapter.data.subtotal, "$ 15.00");
});
