/* @odoo-module */

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { CONNECTION_TYPES } from "./rtc_service";

const PROTOCOLS_TEXT = { host: "HOST", srflx: "STUN", prflx: "STUN", relay: "TURN" };

export class CallContextMenu extends Component {
    static props = ["rtcSession", "close?"];
    static template = "discuss.CallContextMenu";

    updateStatsTimeout;

    setup() {
        this.userSettings = useState(useService("mail.user_settings"));
        this.rtc = useState(useService("mail.rtc"));
        this.state = useState({
            localCandidateType: undefined,
            remoteCandidateType: undefined,
            dataChannelState: undefined,
            packetsReceived: undefined,
            packetsSent: undefined,
            dtlsState: undefined,
            iceState: undefined,
            iceGatheringState: undefined,
        });
        onMounted(() => {
            if (!this.env.debug) {
                return;
            }
            this.updateStats();
            this.updateStatsTimeout = browser.setInterval(() => this.updateStats(), 3000);
        });
        onWillUnmount(() => browser.clearInterval(this.updateStatsTimeout));
    }

    get connectionState() {
        if (this.rtc.state.connectionType === CONNECTION_TYPES.SERVER) {
            return this.rtc.state.rtcServer?.connectionState;
        } else {
            return this.props.rtcSession?.connectionState;
        }
    }

    get inboundConnectionTypeText() {
        if (!this.state.remoteCandidateType) {
            return _t("no connection");
        }
        return sprintf(_t("%(candidateType)s (%(protocol)s)"), {
            candidateType: this.state.remoteCandidateType,
            protocol: PROTOCOLS_TEXT[this.state.remoteCandidateType],
        });
    }

    get outboundConnectionTypeText() {
        if (!this.state.localCandidateType) {
            return _t("no connection");
        }
        return sprintf(_t("%(candidateType)s (%(protocol)s)"), {
            candidateType: this.state.localCandidateType,
            protocol: PROTOCOLS_TEXT[this.state.localCandidateType],
        });
    }

    get peerConnection() {
        if (this.rtc.state.connectionType === CONNECTION_TYPES.SERVER) {
            return this.rtc.state.rtcServer?.peerConnection;
        } else {
            return this.props.rtcSession?.peerConnection;
        }
    }

    get volume() {
        return this.userSettings.getVolume(this.props.rtcSession);
    }

    onChangeVolume(ev) {
        const volume = Number(ev.target.value);
        this.userSettings.saveVolumeSetting({
            guestId: this.props.rtcSession?.guestId,
            partnerId: this.props.rtcSession?.partnerId,
            volume,
        });
        this.props.rtcSession.volume = volume;
    }

    async updateStats() {
        this.state.localCandidateType = undefined;
        this.state.remoteCandidateType = undefined;
        this.state.dataChannelState = undefined;
        this.state.packetsReceived = undefined;
        this.state.packetsSent = undefined;
        this.state.dtlsState = undefined;
        this.state.iceState = undefined;
        this.state.iceGatheringState = undefined;
        if (!this.peerConnection) {
            return;
        }
        let stats;
        try {
            stats = await this.peerConnection.getStats();
        } catch {
            return;
        }
        this.iceGatheringState = this.peerConnection.iceGatheringState;
        for (const value of stats.values() || []) {
            switch (value.type) {
                case "candidate-pair":
                    if (value.state === "succeeded" && value.localCandidateId) {
                        this.state.localCandidateType =
                            stats.get(value.localCandidateId)?.candidateType || "";
                        this.state.remoteCandidateType =
                            stats.get(value.remoteCandidateId)?.candidateType || "";
                    }
                    break;
                case "data-channel":
                    this.state.dataChannelState = value.state;
                    break;
                case "transport":
                    this.state.dtlsState = value.dtlsState;
                    this.state.iceState = value.iceState;
                    this.state.packetsReceived = value.packetsReceived;
                    this.state.packetsSent = value.packetsSent;
                    break;
            }
        }
    }
}
