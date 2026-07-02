export class MockRTCDataChannel {
    constructor({ readyState = "open" } = {}) {
        this.readyState = readyState;
        this.onopen = null;
        this.onclose = null;
        this.onmessage = null;
        this._sent = [];
    }

    send(msg) {
        this._sent.push(msg);
    }

    close() {
        this.readyState = "closed";
    }

    triggerOpen() {
        this.readyState = "open";
        this.onopen?.();
    }
    triggerClose() {
        this.readyState = "closed";
        this.onclose?.();
    }
    triggerMessage(data) {
        this.onmessage?.({ data });
    }
}

export class MockRTCPeerConnection {
    constructor({ connectionState = "new", remoteDescription = null } = {}) {
        this.connectionState = connectionState;
        this.signalingState = "stable";
        this.remoteDescription = remoteDescription;
        this.localDescription = null;
        this.onicecandidate = null;
        this.ondatachannel = null;
        this.onconnectionstatechange = null;
        this._candidates = [];
        this._channel = null;
    }

    async createOffer() {
        return { type: "offer", sdp: "mock-sdp-offer" };
    }

    async createAnswer() {
        return { type: "answer", sdp: "mock-sdp-answer" };
    }

    async setLocalDescription(sdp) {
        this.localDescription = sdp;
        this.signalingState = sdp.type === "offer" ? "have-local-offer" : "stable";
    }

    async setRemoteDescription(sdp) {
        this.remoteDescription = sdp;
        this.signalingState = sdp.type === "offer" ? "have-remote-offer" : "stable";
    }

    async addIceCandidate(candidate) {
        this._candidates.push(candidate);
    }

    createDataChannel() {
        this._channel = new MockRTCDataChannel();
        return this._channel;
    }

    close() {
        this.connectionState = "closed";
    }

    triggerConnectionStateChange(state) {
        this.connectionState = state;
        this.onconnectionstatechange?.();
    }

    triggerIceCandidate(candidate) {
        this.onicecandidate?.({ candidate });
    }

    triggerDataChannel(channel = new MockRTCDataChannel()) {
        this.ondatachannel?.({ channel });
        return channel;
    }
}
