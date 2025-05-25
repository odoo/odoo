import { registry } from "@web/core/registry";
import { WebRTCDataChannel } from "@point_of_sale/app/webrtc/webrtc";

export const webRTCDataChannelService = {
    dependencies: WebRTCDataChannel.serviceDependencies,
    async start(env, deps) {
        return new WebRTCDataChannel(env, deps).ready;
    },
};

registry.category("services").add("webrtc_data_channel", webRTCDataChannelService);
