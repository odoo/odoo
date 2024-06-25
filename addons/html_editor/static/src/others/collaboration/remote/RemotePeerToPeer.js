import { PeerToPeer } from "./PeerToPeer";
import { RemoteInterface, dispatchEvent } from "./remoteHelpers";

export class RemotePeerToPeer extends RemoteInterface {
    async start() {
        this.ptp = new PeerToPeer({
            currentPeerId: this.config.peerId,
            peerConnectionConfig: { iceServers: this.config.peerToPeerConfig.iceServers },
            broadcastAll: this.config.peerToPeerConfig.broadcastAll,
            onNotification: this.handleNotification.bind(this),
        });
        this.peerTryingToJoin = new Set();
    }
    stop() {
        this.ptp.stop();
    }
    ptpJoin() {
        this.ptp.notifyAllPeers("ptp_join");
    }
    notifyAllPeers(notificationName, notificationPayload) {
        this.ptp.notifyAllPeers(notificationName, notificationPayload, { transport: "rtc" });
    }
    notifyPeer(peerId, notificationName, notificationPayload) {
        this.ptp.notifyPeer(peerId, notificationName, notificationPayload, { transport: "rtc" });
    }
    /**
     * This method is used from outside (eg. the odoo bus) to exchange signaling
     * data before the notification can be send from the PeerToPeer instance.
     * `this.handleNotification` will be called from `ptp.handleNotification`.
     */
    handleExternalNotification(dataPayload) {
        if (dataPayload.notificationName === "ptp_join") {
            this.peerTryingToJoin.add(dataPayload.fromPeerId);
        }
        this.ptp.handleNotification(dataPayload);
    }
    handleNotification(dataPayload) {
        const isInternal =
            typeof dataPayload.fromPeerId === "undefined" &&
            typeof dataPayload.toPeerId === "undefined";
        const isSelf = dataPayload.fromPeerId === this.config.peerId;
        const isBroadcast = typeof dataPayload.toPeerId === "undefined";
        const isTarget = dataPayload.toPeerId === this.config.peerId;
        const canReceive = isInternal || isTarget || (!isSelf && isBroadcast);
        if (!canReceive) {
            return;
        }
        const handled =
            this.handleDataChannelOpen(dataPayload) || this.handlePtpRemove(dataPayload);
        if (handled) {
            return;
        }
        dispatchEvent(this, "remote-notification", {
            fromPeerId: dataPayload.fromPeerId,
            notificationName: dataPayload.notificationName,
            notificationPayload: dataPayload.notificationPayload,
        });
    }
    handleDataChannelOpen(dataPayload) {
        if (dataPayload.notificationName === "rtc_data_channel_open") {
            const { connectionPeerId } = dataPayload.notificationPayload;
            if (!this.peerTryingToJoin.has(connectionPeerId)) {
                dispatchEvent(this, "ptp-ping", connectionPeerId);
            } else {
                this.peerTryingToJoin.delete(connectionPeerId);
            }
            return true;
        }
    }
    handlePtpRemove(dataPayload) {
        if (dataPayload.notificationName === "ptp_remove") {
            dispatchEvent(this, "remote-notification", {
                fromPeerId: dataPayload.fromPeerId || dataPayload.notificationPayload,
                notificationName: "remove_peer",
            });
            return true;
        }
    }
}
