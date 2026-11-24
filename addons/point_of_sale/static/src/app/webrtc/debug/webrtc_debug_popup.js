import { Component, proxy, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

const STATE_BADGES = {
    connected: "text-bg-success",
    connecting: "text-bg-info",
    disconnected: "text-bg-warning",
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
        this.pos = usePos();
        this.webrtc = this.pos.webrtc;
        this.state = proxy({ tab: "actions" });
    }

    get peers() {
        return [...this.webrtc.peerStates().entries()].map(([id, state]) => ({
            id,
            state,
            badgeClass: STATE_BADGES[state] || "text-bg-secondary",
        }));
    }

    broadcastHi() {
        this.webrtc.broadcast("Hi");
    }

    announce() {
        this.webrtc.announce();
    }
}
