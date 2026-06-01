import { debounce } from "@web/core/utils/timing";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { PeerDto, WebRtcPeer } from "./webrtc_peer";
import { uuidv4 } from "@point_of_sale/utils";

export class WebRtcService {
    static serviceDependencies = ["orm", "bus_service"];

    constructor(env, deps) {
        this.env = env;
        this.orm = deps.orm;
        this.bus = deps.bus_service;
        this.configId = odoo.pos_config_id || session.config_id;
        this.group = odoo.screen_type || session.screen_type;
        this.STUN = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
        this.id = uuidv4();

        this.connections = new Map();
        this._registry = new Map();
        this._snapshotRegistry = new Map();
        this._queue = [];
        this._initialized = false;

        this.debounceSendMessages = debounce(this._flush.bind(this), 300);
        this.ready = this._init();
    }

    get _deviceUuid() {
        return localStorage.getItem("device_uuid");
    }

    // ─── Public API ───────────────────────────────────────────────────────────

    register(name, fn) {
        this._registry.set(name, fn);
        return this; // chainable
    }

    pushMessage(action, args = [], options = {}) {
        this._queue.push({ action, args, options });
    }

    sendToAll(messages) {
        const payload = { type: "batch", messages };
        this.connections.forEach((peer) => peer.send(payload));
    }

    sendToGroup(group, messages) {
        const payload = { type: "batch", messages };
        this.connections.forEach((peer) => {
            if (peer.group === group) {
                peer.send(payload);
            }
        });
    }

    sendToPeer(peerId, messages) {
        const payload = { type: "batch", messages };
        this.connections.get(peerId)?.send(payload);
    }

    registerSnapshot(name, { build, apply }) {
        this._snapshotRegistry.set(name, { build, apply });
        return this;
    }

    sendSnapshot(peerId, name, snapshot) {
        this.connections.get(peerId)?.send({ type: "snapshot", name, snapshot });
    }

    async reAnnounce() {
        if (!this._initialized) {
            return this._announce();
        }
        await this.orm.call("pos.config", "webrtc_announce", [
            this.configId,
            this.id,
            this.group,
            this._deviceUuid,
        ]);
    }

    leave() {
        this._stopHeartbeat();
        this._closeAllConnections();
    }

    // ─── Queue & flush ────────────────────────────────────────────────────────

    _flush() {
        if (this._queue.length === 0) {
            return;
        }

        const batches = this._queue.reduce((acc, msg) => {
            const group = msg.options?.group ?? "all";
            acc[group] = acc[group] || { group, msgs: [] };
            acc[group].msgs.push(msg);
            return acc;
        }, {});

        this._queue = [];

        Object.values(batches).forEach(({ group, msgs }) => {
            const mergedMessages = this._mergeMessages(msgs);
            if (group === "all") {
                this.sendToAll(mergedMessages);
            } else {
                this.sendToGroup(group, mergedMessages);
            }
        });
    }

    _mergeMessages(messages) {
        const syncMessages = [];
        const otherMessages = [];

        for (const msg of messages) {
            if (msg.action === "sync") {
                syncMessages.push(msg);
            } else {
                otherMessages.push({ action: msg.action, args: msg.args });
            }
        }

        if (!syncMessages.length) {
            return otherMessages;
        }

        const syncPayload = syncMessages.reduce((acc, msg) => {
            acc.push(msg.args[0]);
            return acc;
        }, []);
        return [{ action: "sync", args: [syncPayload] }, ...otherMessages];
    }

    // ─── Init ─────────────────────────────────────────────────────────────────

    async _init() {
        if (!this.group) {
            return this;
        }
        await this._announce();
        return this;
    }

    async _announce() {
        const result = await this.orm.call("pos.config", "webrtc_announce", [
            this.configId,
            this.id,
            this.group,
            this._deviceUuid,
        ]);
        this.id = result.uuid;

        this.bus.addChannel(result.bus_channel);
        this.bus.subscribe(`${result.bus_channel}-WEBRTC_PEER_ANNOUNCE`, (payload) => {
            const peer = {
                id: payload.peer_id,
                group: payload.peer_group,
                deviceUuid: payload.peer_device_uuid ?? null,
            };
            if (this._shouldConnect(peer)) {
                this._initiateConnection(peer);
            }
        });
        this.bus.subscribe(`${result.bus_channel}-WEBRTC_SIGNAL`, (payload) => {
            this._handleSignal(payload);
        });

        this._startHeartbeat();
        this._initialized = true;
    }

    async _initiateConnection({ id, group, deviceUuid }, retryCount = 0) {
        if (this.connections.has(id)) {
            this._closeConnection(id);
        }

        const pc = new RTCPeerConnection(this.STUN);
        const channel = pc.createDataChannel("webrtc");

        const peer = this._addPeer(id, { pc, channel, group, deviceUuid });
        peer.retryCount = retryCount;
        if (retryCount > 0) {
            peer.wasConnected = true;
        }

        this._setupChannel(channel, id);
        this._setupPeerConnection(pc, id);

        try {
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            await this._signal(id, {
                type: "offer",
                sdp: pc.localDescription,
                group: this.group,
                deviceUuid: this._deviceUuid,
            });
        } catch {
            // Signal failed (e.g. offline) — remove the half-open entry so
            // the heartbeat or a future re-announce can retry cleanly.
            this._closeConnection(id);
        }
    }

    // ─── Peer connection setup ────────────────────────────────────────────────

    _setupPeerConnection(pc, peerId) {
        pc.ondatachannel = ({ channel }) => this._onDataChannel(peerId, channel);
        pc.onicecandidate = ({ candidate }) => this._onIceCandidate(peerId, candidate);
        pc.onconnectionstatechange = () =>
            this._onConnectionStateChange(peerId, pc.connectionState);
    }

    _onDataChannel(peerId, channel) {
        const peer = this.connections.get(peerId);
        if (peer) {
            peer.channel = channel;
            this._setupChannel(channel, peerId);
        }
    }

    _onIceCandidate(peerId, candidate) {
        if (candidate) {
            this._signal(peerId, { type: "ice", candidate });
        }
    }

    _onConnectionStateChange(peerId, state) {
        if (["disconnected", "failed", "closed"].includes(state)) {
            const peer = this.connections.get(peerId);
            const { wasConnected, retryCount, group, deviceUuid } = peer ?? {};
            this._closeConnection(peerId);
            if (wasConnected && state === "failed") {
                setTimeout(() => {
                    if (!this.connections.has(peerId)) {
                        this._initiateConnection({ id: peerId, group, deviceUuid }, retryCount + 1);
                    }
                }, WebRtcService.ICE_RECONNECT_DELAY);
            }
        }
    }

    // ─── Channel setup ────────────────────────────────────────────────────────

    _setupChannel(channel, peerId) {
        channel.onopen = () => this._onChannelOpen(peerId);
        channel.onclose = () => this._onChannelClose(peerId);
        channel.onmessage = ({ data }) => this._onChannelMessage(peerId, data);
    }

    _onChannelOpen(peerId) {
        const peer = this.connections.get(peerId);
        if (peer) {
            peer.wasConnected = true;
            peer.retryCount = 0;
            for (const [name, { build }] of this._snapshotRegistry) {
                const snapshot = build(new PeerDto(peerId, peer.group, peer.deviceUuid));
                if (snapshot !== null && snapshot !== undefined) {
                    this.sendSnapshot(peerId, name, snapshot);
                }
            }
        }
    }

    _onChannelClose(peerId) {
        this._closeConnection(peerId);
    }

    _onChannelMessage(peerId, data) {
        this._onRemoteMessage(peerId, data);
    }

    // ─── Incoming message handling ────────────────────────────────────────────────

    _onRemoteMessage(from, raw) {
        let payload;
        try {
            payload = JSON.parse(raw);
        } catch {
            console.error(`[WebRTC] Malformed message from ${from}`);
            return;
        }

        switch (payload.type) {
            case "batch":
                this._onBatch(from, payload.messages);
                break;
            case "snapshot": {
                this._onSnapshot(from, payload.name, payload.snapshot);
                break;
            }
            case "ping":
                this._onPing(from);
                break;
            case "pong":
                this._onPong(from);
                break;
            default:
                console.error(`[WebRTC] Unknown message type "${payload.type}" from ${from}`);
        }
    }

    _onBatch(from, messages) {
        const peer = this.connections.get(from);
        const peerDto = new PeerDto(from, peer?.group, peer?.deviceUuid);
        for (const { action, args } of messages) {
            const fn = this._registry.get(action);
            if (!fn) {
                console.error(`[WebRTC] Unknown action "${action}" from ${from}`);
                continue;
            }
            fn(peerDto, ...args);
        }
    }

    _onSnapshot(from, name, snapshot) {
        const handler = this._snapshotRegistry.get(name);
        if (handler) {
            const peer = this.connections.get(from);
            const dto = new PeerDto(from, peer?.group, peer?.deviceUuid);
            handler.apply(dto, snapshot);
        } else {
            console.error(`[WebRTC] Unknown snapshot name "${name}" from ${from}`);
        }
    }

    _onPing(from) {
        this.connections.get(from)?.send({ type: "pong" });
    }

    _onPong(from) {
        const peer = this.connections.get(from);
        if (peer) {
            peer.lastPong = Date.now();
        }
    }

    // ─── Signaling ────────────────────────────────────────────────────────────

    async _signal(target, msg) {
        await this.orm.call("pos.config", "webrtc_signal", [
            this.configId,
            { ...msg, to: target, from: this.id },
        ]);
    }

    async _handleSignal(payload) {
        if (payload.from === this.id || payload.to !== this.id) {
            return;
        }

        switch (payload.type) {
            case "offer":
                return this._onOffer(payload);
            case "answer":
                return this._onAnswer(payload);
            case "ice":
                return this._onIce(payload);
            default:
                console.error(`[WebRTC] Unknown signal type: ${payload.type}`);
        }
    }

    async _onOffer(payload) {
        this._closeConnection(payload.from);

        const pc = new RTCPeerConnection(this.STUN);
        const peer = this._addPeer(payload.from, {
            pc,
            group: payload.group,
            deviceUuid: payload.deviceUuid,
        });
        this._setupPeerConnection(pc, payload.from);

        try {
            await pc.setRemoteDescription(payload.sdp);
            await peer.flushPendingCandidates();
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            await this._signal(payload.from, { type: "answer", sdp: pc.localDescription });
        } catch {
            this._closeConnection(payload.from);
        }
    }

    async _onAnswer(payload) {
        const peer = this.connections.get(payload.from);
        if (peer?.pc?.signalingState === "have-local-offer") {
            try {
                await peer.pc.setRemoteDescription(payload.sdp);
                await peer.flushPendingCandidates();
            } catch {
                this._closeConnection(payload.from);
            }
        }
    }

    async _onIce(payload) {
        await this.connections.get(payload.from)?.addIceCandidate(payload.candidate);
    }

    // ─── Heartbeat ────────────────────────────────────────────────────────────

    static HEARTBEAT_INTERVAL = 30_000;
    static ICE_RECONNECT_DELAY = 5_000;

    _startHeartbeat() {
        this._heartbeatTimer = setInterval(() => {
            this._cleanupZombies();
            this._sendPing();
        }, WebRtcService.HEARTBEAT_INTERVAL);
    }

    _stopHeartbeat() {
        clearInterval(this._heartbeatTimer);
        this._heartbeatTimer = null;
    }

    _sendPing() {
        this.connections.forEach((peer) => {
            peer.send({ type: "ping" });
        });
    }

    _cleanupZombies() {
        const threshold = Date.now() - 2 * WebRtcService.HEARTBEAT_INTERVAL;
        for (const [peerId, peer] of this.connections.entries()) {
            if (peer.lastPong < threshold) {
                const { wasConnected, retryCount, group, deviceUuid } = peer;
                this._closeConnection(peerId);
                if (wasConnected) {
                    const delay =
                        retryCount === 0
                            ? 0
                            : Math.min(5_000 * Math.pow(2, retryCount - 1), 60_000);
                    setTimeout(() => {
                        if (!this.connections.has(peerId)) {
                            this._initiateConnection(
                                { id: peerId, group, deviceUuid },
                                retryCount + 1
                            );
                        }
                    }, delay);
                }
            }
        }
    }

    // ─── Connection ──────────────────────────────────────────────────────────

    _shouldConnect({ id, group, deviceUuid }) {
        if (id === this.id) {
            return false;
        }
        if (this.group === "terminal" && group === "terminal") {
            return true;
        }
        if (
            (this.group === "customer_display" && group === "terminal") ||
            (this.group === "terminal" && group === "customer_display")
        ) {
            return this._deviceUuid === deviceUuid;
        }
        return false;
    }

    _addPeer(peerId, data) {
        const peer = new WebRtcPeer(peerId, data);
        this.connections.set(peerId, peer);
        return peer;
    }

    _closeAllConnections() {
        this.connections.forEach((peer) => peer.close());
        this.connections.clear();
    }

    _closeConnection(peerId) {
        this.connections.get(peerId)?.close();
        this.connections.delete(peerId);
    }
}

// ─── Odoo service registration ────────────────────────────────────────────────

export const webRtcService = {
    dependencies: WebRtcService.serviceDependencies,
    async start(env, deps) {
        return new WebRtcService(env, deps).ready;
    },
};

registry.category("services").add("webrtc", webRtcService);
