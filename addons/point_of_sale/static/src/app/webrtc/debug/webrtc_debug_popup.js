import { Component, proxy, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { LOG_TYPES } from "@point_of_sale/app/webrtc/webrtc_log_plugin";
import { useWebRtc } from "@point_of_sale/app/webrtc/webrtc_plugin";

const STATE_BADGES = {
    connected: "text-bg-success",
    connecting: "text-bg-info",
    disconnected: "text-bg-warning",
    reconnecting: "text-bg-warning",
    failed: "text-bg-danger",
    closed: "text-bg-danger",
};

export class WebrtcDebugPopup extends Component {
    static template = "point_of_sale.WebrtcDebugPopup";
    static components = { Dialog };
    props = useProps({
        close: t.function().optional(),
    });

    setup() {
        this.webrtc = useWebRtc();
        this.logger = this.webrtc.logger;
        this.logTypes = Object.keys(LOG_TYPES);
        this.state = proxy({ tab: "actions" });
    }

    get peers() {
        return [...this.webrtc.peerStates().entries()].map(([id, state]) => ({
            id,
            state,
            badgeClass: STATE_BADGES[state] || "text-bg-secondary",
        }));
    }

    logBadgeClass(type) {
        return `text-bg-${LOG_TYPES[type]?.badge || "secondary"}`;
    }

    formatTime(time) {
        return time.toLocaleTimeString([], { hour12: false });
    }

    broadcastHi() {
        this.webrtc.broadcast("Hi");
    }

    announce() {
        this.webrtc.announce();
    }
}
