import { expect, test } from "@odoo/hoot";
import { MockWebRtcMesh } from "../webrtc/utils/mock_webrtc_mesh";
import { CustomerDisplayPosAdapter } from "@point_of_sale/app/customer_display/customer_display_adapter";
import { CustomerDisplayDataService } from "@point_of_sale/customer_display/customer_display_data_service";

// Integration tests for the terminal → customer display channel.
// Use real services wired through MockWebRtcMesh to prove the full chain works:
//   snapshot path:   CustomerDisplayPosAdapter.build → sendSnapshot → CustomerDisplayDataService.apply
//   live path:       adapter.dispatch → _flush → wire → _onBatch → update_customer_display handler

const makeTerminal = async () => {
    const mesh = new MockWebRtcMesh();
    await mesh.addPeer("pos-1", "terminal", { deviceUuid: "test-uuid" });
    const terminal = mesh.peers.get("pos-1").service;
    const adapter = new CustomerDisplayPosAdapter(terminal);
    return { mesh, terminal, adapter };
};

const connectDisplay = async (mesh, id = "display-1") => {
    let displayData;
    await mesh.addPeer(id, "customer_display", {
        deviceUuid: "test-uuid",
        setup: async (service) => {
            displayData = await CustomerDisplayDataService.setup({}, { webrtc: service });
        },
    });
    return displayData;
};

test("display receives live update when terminal dispatches after connect", async () => {
    const { mesh, terminal, adapter } = await makeTerminal();

    const displayData = await connectDisplay(mesh);

    adapter.data = { amount: "15.00" };
    adapter.dispatch();
    terminal._flush();

    expect(displayData).toEqual({ amount: "15.00" });
});

test("display receives terminal state as snapshot on connect", async () => {
    const { mesh, adapter } = await makeTerminal();
    adapter.data = { amount: "10.00" };

    const displayData = await connectDisplay(mesh);
    expect(displayData).toEqual({ amount: "10.00" });
});

test("reconnecting display receives updated snapshot, not stale state", async () => {
    const { mesh, terminal, adapter } = await makeTerminal();
    adapter.data = { amount: "10.00" };

    const data1 = await connectDisplay(mesh, "display-1");
    expect(data1).toEqual({ amount: "10.00" });

    terminal._closeConnection("display-1");
    adapter.data = { amount: "25.00" };

    const data2 = await connectDisplay(mesh, "display-2");
    expect(data2).toEqual({ amount: "25.00" });
});
