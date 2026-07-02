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
    }

    send(message) {
        if (this.channel?.readyState === "open") {
            this.channel.send(JSON.stringify(message));
            return true;
        }
        return false;
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
