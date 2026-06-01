import {
    MockServer,
    makeMockServer,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { WebRtcService } from "@point_of_sale/app/webrtc/webrtc_service";
import { CustomerDisplayDataService } from "@point_of_sale/customer_display/customer_display_data_service";
import { MockRTCDataChannel, MockRTCPeerConnection } from "./mock_webrtc";

export async function makeWebrtcService({ id = "self-id", group = "terminal", deviceUuid } = {}) {
    if (deviceUuid) {
        patchWithCleanup(localStorage, {
            getItem: (key) => (key === "device_uuid" ? deviceUuid : null),
        });
        patchWithCleanup(session, { device_uuid: deviceUuid });
    }
    const bus = { addChannel() {}, subscribe() {} };
    patchWithCleanup(odoo, { pos_config_id: 1, screen_type: group, access_token: "pos-ch" });

    onRpc("/pos/webrtc/announce", () => ({}));
    onRpc("/pos/webrtc/signal", () => ({}));
    onRpc("/pos_customer_display/webrtc/announce", () => ({}));
    onRpc("/pos_customer_display/webrtc/signal", () => ({}));
    if (!MockServer.current) {
        await makeMockServer();
    }

    const service = new WebRtcService({}, { bus_service: bus });
    await service.ready;

    service._stopHeartbeat();
    return service;
}

export async function makeCustomerDisplayService({ id, deviceUuid = "my-uuid" } = {}) {
    const webrtc = await makeWebrtcService({ id, group: "customer_display", deviceUuid });
    const data = await CustomerDisplayDataService.setup({}, { webrtc });
    return { webrtc, data };
}

export function addFakePeer(
    webrtc,
    peerId,
    { group = "terminal", deviceUuid = null, readyState, connectionState, remoteDescription } = {}
) {
    const pc = new MockRTCPeerConnection({ connectionState, remoteDescription });
    const channel = new MockRTCDataChannel({ readyState });
    return webrtc._addPeer(peerId, { pc, channel, group, deviceUuid });
}
