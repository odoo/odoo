import { uuidv4 } from "@point_of_sale/utils";

export class PeerDto {
    constructor(id, group, deviceUuid) {
        this.id = id;
        this.group = group ?? null;
        this.deviceUuid = deviceUuid ?? null;
    }
}

export class WebRtcPeer {
    constructor(id, data) {
        this.id = id;
        this.pc = data.pc ?? null;
        this.channel = data.channel ?? null;
        this.group = data.group ?? null;
        this.deviceUuid = data.deviceUuid ?? null;
        this.pendingCandidates = [];
        this.lastPong = Date.now(); // gives a full heartbeat interval grace period before zombie cleanup
        this.wasConnected = false;
        this.retryCount = 0;
        this.snapshotsSent = false;
    }

    static MAX_CHUNK_SIZE = 15_000;

    send(message) {
        if (this.channel?.readyState !== "open") {
            return false;
        }
        const payload = JSON.stringify(message);
        if (payload.length <= WebRtcPeer.MAX_CHUNK_SIZE) {
            this.channel.send(payload);
            return true;
        }
        const cid = uuidv4();
        const total = Math.ceil(payload.length / WebRtcPeer.MAX_CHUNK_SIZE);
        for (let index = 0; index < total; index++) {
            const data = payload.slice(
                index * WebRtcPeer.MAX_CHUNK_SIZE,
                (index + 1) * WebRtcPeer.MAX_CHUNK_SIZE
            );
            this.channel.send(JSON.stringify({ type: "chunk", cid, index, total, data }));
        }
        return true;
    }

    async addIceCandidate(candidate) {
        if (!this.pc.remoteDescription) {
            this.pendingCandidates.push(candidate);
            return;
        }
        if (this.pc.connectionState !== "closed") {
            await this.pc.addIceCandidate(candidate);
        }
    }

    async flushPendingCandidates() {
        if (!this.pendingCandidates.length) {
            return;
        }
        const pending = this.pendingCandidates;
        this.pendingCandidates = [];
        for (const candidate of pending) {
            await this.addIceCandidate(candidate);
        }
    }

    close() {
        if (this.channel && this.channel.readyState !== "closed") {
            this.channel.onclose = null;
            this.channel.close();
        }
        if (this.pc && this.pc.connectionState !== "closed") {
            this.pc.onconnectionstatechange = null;
            this.pc.close();
        }
    }
}
