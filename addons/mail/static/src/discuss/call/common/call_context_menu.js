import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { CONNECTION_TYPES } from "@mail/discuss/call/common/rtc_service";

const PROTOCOLS_TEXT = { host: "HOST", srflx: "STUN", prflx: "STUN", relay: "TURN" };

export class CallContextMenu extends Component {
    static props = ["rtcSession", "close?"];
    static template = "discuss.CallContextMenu";

    updateStatsTimeout;
    rtcConnectionTypes = CONNECTION_TYPES;

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.state = useState({
            downloadStats: {},
            uploadStats: {},
            producerStats: {},
            peerStats: {},
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

    get isSelf() {
        return this.rtc.selfSession?.eq(this.props.rtcSession);
    }

    get inboundConnectionTypeText() {
        const candidateType =
            this.rtc.state.connectionType === CONNECTION_TYPES.SERVER
                ? this.state.downloadStats.remoteCandidateType
                : this.state.peerStats.remoteCandidateType;
        return this.formatProtocol(candidateType);
    }

    get outboundConnectionTypeText() {
        const candidateType =
            this.rtc.state.connectionType === CONNECTION_TYPES.SERVER
                ? this.state.uploadStats.localCandidateType
                : this.state.peerStats.localCandidateType;
        return this.formatProtocol(candidateType);
    }

    get volume() {
        return this.store.settings.getVolume(this.props.rtcSession);
    }

    /**
     * @param {string} candidateType
     * @returns {string} a formatted string that describes the connection type e.g: "prflx (STUN)"
     */
    formatProtocol(candidateType) {
        if (!candidateType) {
            return _t("no connection");
        }
        return _t("%(candidateType)s (%(protocol)s)", {
            candidateType,
            protocol: PROTOCOLS_TEXT[candidateType],
        });
    }

    async updateStats() {
        if (this.rtc.selfSession?.eq(this.props.rtcSession)) {
            if (this.rtc.sfuClient) {
                const { uploadStats, downloadStats, ...producerStats } =
                    await this.rtc.sfuClient.getStats();
                const formattedUploadStats = {};
                for (const value of uploadStats.values?.() || []) {
                    switch (value.type) {
                        case "candidate-pair":
                            if (value.state === "succeeded" && value.localCandidateId) {
                                formattedUploadStats.localCandidateType =
                                    uploadStats.get(value.localCandidateId)?.candidateType || "";
                                formattedUploadStats.availableOutgoingBitrate =
                                    value.availableOutgoingBitrate;
                            }
                            break;
                        case "transport":
                            formattedUploadStats.dtlsState = value.dtlsState;
                            formattedUploadStats.iceState = value.iceState;
                            formattedUploadStats.packetsSent = value.packetsSent;
                            break;
                    }
                }
                const formattedDownloadStats = {};
                for (const value of downloadStats.values?.() || []) {
                    switch (value.type) {
                        case "candidate-pair":
                            if (value.state === "succeeded" && value.localCandidateId) {
                                formattedDownloadStats.remoteCandidateType =
                                    downloadStats.get(value.remoteCandidateId)?.candidateType || "";
                            }
                            break;
                        case "transport":
                            formattedDownloadStats.dtlsState = value.dtlsState;
                            formattedDownloadStats.iceState = value.iceState;
                            formattedDownloadStats.packetsReceived = value.packetsReceived;
                            break;
                    }
                }
                const formattedProducerStats = {};
                for (const [type, stat] of Object.entries(producerStats)) {
                    const currentTypeStats = {};
                    for (const value of stat.values()) {
                        switch (value.type) {
                            case "codec":
                                currentTypeStats.codec = value.mimeType;
                                currentTypeStats.clockRate = value.clockRate;
                                break;
                        }
                    }
                    formattedProducerStats[type] = currentTypeStats;
                }
                this.state.uploadStats = formattedUploadStats;
                this.state.downloadStats = formattedDownloadStats;
                this.state.producerStats = formattedProducerStats;
            }
            return;
        }
        this.state.peerStats = await this.rtc.p2pService.getFormattedStats(
            this.props.rtcSession.id
        );
    }

    onChangeVolume(ev) {
        const volume = Number(ev.target.value);
        this.store.settings.saveVolumeSetting({
            guestId: this.props.rtcSession?.guestId,
            partnerId: this.props.rtcSession?.partnerId,
            volume,
        });
        this.props.rtcSession.volume = volume;
    }
}
