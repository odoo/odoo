import { Component, onWillDestroy, proxy, props, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

const FAILED_STATES = ["failed", "closed"];

export class WebrtcDebugPopup extends Component {
    static template = "point_of_sale.WebrtcDebugPopup";
    static components = { Dialog };
    props = props({ close: t.function(), webrtc: t.object() });

    setup() {
        this.state = proxy({ peer: null });
        this._onReply = (entry) => {
            const conn = this.state.peer.connections.find((c) => c.id === entry.id);
            if (conn) {
                conn.theirState = entry.connection?.state ?? "closed";
                conn.deviceUuid = entry.deviceUuid ?? conn.deviceUuid;
            }
        };
        this.refresh();
        onWillDestroy(() => this.props.webrtc.stopDebugQuery(this._onReply));
    }

    refresh() {
        const peer = this.props.webrtc.startDebugQuery(this._onReply);
        peer.connections = peer.connections.map((conn) => ({ ...conn, theirState: undefined }));
        this.state.peer = peer;
    }

    stateBadge(state) {
        if (state === undefined) {
            return { class: "text-bg-secondary", label: "waiting" };
        }
        if (state === "connected") {
            return { class: "text-bg-success", label: state };
        }
        if (FAILED_STATES.includes(state)) {
            return { class: "text-bg-danger", label: state };
        }
        if (state === "disconnected") {
            return { class: "text-bg-warning", label: state };
        }
        return { class: "text-bg-secondary", label: state };
    }
}
