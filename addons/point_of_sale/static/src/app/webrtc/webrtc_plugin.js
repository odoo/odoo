import { Plugin, onWillDestroy, signal, useListener, usePlugin } from "@odoo/owl";
import { BusPlugin } from "@bus/services/bus_plugin";
import { rpc } from "@web/core/network/rpc";
import { services } from "@web/core/services";
import { session } from "@web/session";
import { uuidv4 } from "@point_of_sale/utils";
import { WebRtcLogPlugin } from "@point_of_sale/app/webrtc/webrtc_log_plugin";

/** Bus channel of the signaling messages of a config. */
export function webrtcChannel(configId) {
    return `pos.config_webrtc_${configId}`;
}

/** Notification type of the signaling messages of a config. */
export function webrtcSignalType(configId) {
    return `WEBRTC_SIGNAL-${configId}`;
}

// Time given to the other device to answer an offer, or to send an offer
// after an announce sent to it.
const ANSWER_TIMEOUT = 15000;
// Time given to the gathering of the network candidates: after it, the offer
// or the answer is sent with the candidates found so far.
const GATHERING_TIMEOUT = 5000;
// Time given to a connection to get connected, once the offer is answered.
const CONNECTION_TIMEOUT = 15000;
// Delays before the next attempts to connect to a device; once all are
// used, the device gives up until the other one announces itself again.
// Also used to announce the device again when its announce fails.
const RETRY_DELAYS = [1000, 2000, 4000, 8000];
// A device pings the other ones this often over the data channel...
const PING_INTERVAL = 10000;
// ... and reconnects to one it heard nothing from for this long.
const HEARTBEAT_TIMEOUT = 30000;

/**
 * Peer-to-peer connections between the devices of a PoS config.
 *
 * The server only relays the signaling, on the bus channel of the config:
 * 1. a device that starts broadcasts an `announce`;
 * 2. for each pair of devices, the one with the smaller id sends the `offer`
 *    (the other one answers the announce with its own, sent to the newcomer
 *    only), so two devices never send an offer to each other at the same time;
 * 3. the other device replies with an `answer`, and the data channel opens.
 *
 * Each offer has an `attempt` number, that its answer repeats: an answer to an
 * offer that was replaced meanwhile is ignored, as it doesn't match the
 * connection in progress.
 *
 * A signaling message can be lost: the device waiting for the answer (or, on
 * the side of the bigger id, for the offer) gives up the attempt after a
 * while, and tries again a few times, waiting longer each time (see
 * `failAttempt`). The smaller id retries with a new offer, the bigger id with
 * a new announce sent to the other device.
 *
 * A connection that fails, whose data channel closes, or that doesn't get
 * connected in time once the offer is answered, is rebuilt with the same
 * retries. A device that leaves says "bye" to the other ones first, so
 * that they don't try to reconnect to it.
 *
 * A connection can also look fine while the other device is gone: its page
 * is frozen (its network still answers the checks of the browser), or it
 * crashed and the browser hasn't noticed yet. Each device pings the other
 * ones over the data channel, which answer at once: a connection that receives
 * nothing for too long is rebuilt the same way.
 *
 * A device announces itself again when the bus connects again: an announce
 * from a device already connected is ignored, the connection is kept. A
 * failed announce is also tried again a few times, as the bus may stay
 * connected.
 *
 * In a browser without WebRTC, the device doesn't announce itself, so that
 * the other devices don't try to connect to it.
 *
 * The network candidates are gathered before sending the offer and the answer,
 * so that they are part of the session description and need no message of
 * their own. No STUN server is used: the devices are expected to be on the
 * same local network.
 */
export class WebRtcPlugin extends Plugin {
    bus = usePlugin(BusPlugin);
    logger = usePlugin(WebRtcLogPlugin);
    peerStates = signal.Map(new Map());

    setup() {
        this.id = this.newId();
        this.configId = null;
        /**
         * @type {Map<string, {
         *  pc: RTCPeerConnection,
         *  channel: RTCDataChannel|null,
         *  attempt: number,
         *  pingTimer: number|null,
         *  silenceTimer: number|null,
         * }>}
         */
        this.peers = new Map();
        // Number of the last offer sent, see `onAnswer`.
        this.lastAttempt = 0;
        /**
         * Devices not connected yet: failed attempts, and the timer of the
         * attempt in progress or of the next one.
         * @type {Map<string, {failures: number, timer: number|null}>}
         */
        this.retries = new Map();
        // Set when the bus disconnects or when an announce fails: the device
        // announces itself again once the bus is connected.
        this.shouldAnnounceAgain = false;
        // Failed announces in a row, and the timer of the next one.
        this.announceRetry = { failures: 0, timer: null };

        useListener(window, "pagehide", () => this.stop("pagehide"));
        useListener(window, "pageshow", ({ persisted }) => persisted && this.resume());
        useListener(this.bus, "BUS:DISCONNECT", () => (this.shouldAnnounceAgain = true));
        // After a reconnection (e.g. server restarted) or a new connection
        // (e.g. back online). Not after the first connection, unless the
        // announce failed meanwhile.
        useListener(this.bus, "BUS:RECONNECT", () => this.onBusConnected());
        useListener(this.bus, "BUS:CONNECT", () => this.onBusConnected());
        onWillDestroy(() => this.stop("destroyed"));
    }

    /**
     * @param {Object} params
     * @param {number} params.configId
     */
    start({ configId }) {
        if (!window.RTCPeerConnection) {
            this.logger.log("lifecycle", "WebRTC not supported by this browser");
            return;
        }
        this.configId = configId;
        // Not the access token channel of the config: the customer display and
        // the self order know it, and would see the network addresses of the
        // devices. The server only gives this one to the users of the config.
        this.bus.addChannel(webrtcChannel(configId));
        this.bus.subscribe(webrtcSignalType(configId), (message) => this.onSignal(message));
        this.tryAnnounce();
    }

    /**
     * A new id for this device: the server only relays the messages of an
     * id that ends with the tag of its session, so that another user can't
     * send messages as this device.
     */
    newId() {
        return `${uuidv4()}.${session.pos_webrtc_tag}`;
    }

    resume() {
        if (!this.configId) {
            return;
        }
        // Leaving the page closed the connections, but the other devices may
        // not have noticed it yet: they would ignore the announce of a device
        // they still have a connection to. A new id makes it a new device.
        this.id = this.newId();
        this.logger.log(
            "lifecycle",
            `restored from the back/forward cache, new id ${this.logger.shortId(this.id)}`
        );
        this.tryAnnounce();
    }

    /**
     * Announces the device again once the bus is back: its announce may have
     * failed while the server was unreachable, leaving it alone. The devices
     * already connected to it keep their connection (see `onAnnounce`).
     */
    onBusConnected() {
        if (!this.shouldAnnounceAgain || !this.configId) {
            return;
        }
        this.logger.log("lifecycle", "bus connected again");
        this.tryAnnounce();
    }

    announce() {
        return this.signal({ type: "announce" });
    }

    /**
     * Announces the device, and tries again later if it fails: unless the
     * bus connects again meanwhile, nobody would know the device.
     */
    async tryAnnounce() {
        // An announce is on its way: the bus connecting again meanwhile
        // doesn't need another one.
        this.shouldAnnounceAgain = false;
        clearTimeout(this.announceRetry.timer);
        this.announceRetry.timer = null;
        try {
            await this.announce();
            this.announceRetry.failures = 0;
        } catch (error) {
            this.shouldAnnounceAgain = true;
            this.logger.logError("Failed to announce", error);
            this.retryAnnounce();
        }
    }

    retryAnnounce() {
        const retry = this.announceRetry;
        retry.failures++;
        if (retry.failures > RETRY_DELAYS.length) {
            // Until the bus connects again.
            this.logger.log("lifecycle", `announce: gave up after ${retry.failures} attempts`);
            retry.failures = 0;
            return;
        }
        const delay = RETRY_DELAYS[retry.failures - 1];
        this.logger.log("lifecycle", `announcing again in ${delay / 1000} s`);
        retry.timer = setTimeout(() => {
            retry.timer = null;
            this.tryAnnounce();
        }, delay);
    }

    /**
     * Closes the connections to all the devices.
     *
     * @param {string} reason - for the logs
     */
    stop(reason) {
        this.logger.log("lifecycle", `stopped: ${reason}`);
        clearTimeout(this.announceRetry.timer);
        this.announceRetry = { failures: 0, timer: null };
        for (const peerId of this.retries.keys()) {
            this.resetRetries(peerId);
        }
        for (const [peerId, { channel }] of this.peers) {
            if (channel?.readyState === "open") {
                this.sendBye(peerId, channel);
            }
            this.closePeer(peerId, "stopped");
        }
    }

    /**
     * Tells `peerId` that this device leaves: without it, the closed channel
     * would look broken, and the other device would try to reconnect.
     */
    sendBye(peerId, channel) {
        try {
            channel.send(JSON.stringify({ type: "bye" }));
        } catch (error) {
            this.logger.logError("Failed to say bye", error, peerId);
        }
    }

    /**
     * Sends a text to every connected device. It isn't kept for the ones
     * whose channel isn't open (yet): it would arrive late, maybe outdated.
     */
    broadcast(text) {
        for (const [peerId, { channel }] of this.peers) {
            if (channel?.readyState !== "open") {
                const state = channel ? `channel ${channel.readyState}` : "no channel";
                const to = this.logger.shortId(peerId);
                this.logger.log("message", `not sent "${text}" to ${to}: ${state}`, peerId);
                continue;
            }
            try {
                this.sendText(peerId, channel, text);
            } catch (error) {
                // E.g. the send buffer is full: the next message may go through.
                this.logger.logError(`Failed to send "${text}"`, error, peerId);
            }
        }
    }

    sendText(peerId, channel, text) {
        channel.send(JSON.stringify({ type: "text", text }));
        this.logger.log("message", `sent "${text}" to ${this.logger.shortId(peerId)}`, peerId);
    }

    // ─── Signaling ────────────────────────────────────────────────────────────

    async signal(message) {
        await rpc("/pos/webrtc/signal", {
            config_id: this.configId,
            message: { ...message, from: this.id },
        });
        this.logger.log(
            "signal",
            `sent ${message.type} to ${message.to ? this.logger.shortId(message.to) : "all"}`,
            message.to
        );
    }

    onSignal(message) {
        if (message.from === this.id || (message.to && message.to !== this.id)) {
            return;
        }
        const from = this.logger.shortId(message.from);
        const toAll = message.to ? "" : " to all";
        this.logger.log("signal", `received ${message.type} from ${from}${toAll}`, message.from);
        switch (message.type) {
            case "announce":
                return this.onAnnounce(message);
            case "offer":
                return this.onOffer(message);
            case "answer":
                return this.onAnswer(message);
        }
    }

    onAnnounce({ from, to }) {
        const pc = this.peers.get(from)?.pc;
        if (pc) {
            // A device announces itself again, e.g. when its websocket
            // reconnects: the connection to it doesn't use the server, keep it.
            // Failed and closed connections are already removed from the peers.
            const reason = `existing connection (${pc.connectionState})`;
            const text = `ignored announce from ${this.logger.shortId(from)}: ${reason}`;
            this.logger.log("signal", text, from);
            return;
        }
        if (this.id < from) {
            this.resetRetries(from);
            this.connect(from);
        } else if (!to) {
            // Let the newcomer send the offer, since its id is the smaller one.
            this.resetRetries(from);
            this.announceTo(from);
        }
    }

    /**
     * Asks `peerId`, a smaller id, to send an offer.
     */
    announceTo(peerId) {
        this.setRetryTimer(peerId, ANSWER_TIMEOUT, () => this.failAttempt(peerId, "no offer"));
        this.signal({ type: "announce", to: peerId }).catch((error) =>
            this.logger.logError("Failed to announce", error, peerId)
        );
    }

    async connect(peerId) {
        this.closePeer(peerId, "replaced");
        this.logger.log("peer", "creating offer", peerId);
        this.setRetryTimer(peerId, ANSWER_TIMEOUT, () => this.failAttempt(peerId, "no answer"));
        let pc = null;
        try {
            const attempt = ++this.lastAttempt;
            pc = this.createPeer(peerId, attempt);
            this.setupChannel(peerId, pc.createDataChannel("pos"));
            await pc.setLocalDescription(await pc.createOffer());
            await this.waitIceGathering(peerId, pc);
            if (!this.isCurrent(peerId, pc)) {
                return;
            }
            const sdp = pc.localDescription.toJSON();
            await this.signal({ type: "offer", to: peerId, attempt, sdp });
        } catch (error) {
            // A connection closed meanwhile fails: nothing to report.
            if (pc && !this.isCurrent(peerId, pc)) {
                return;
            }
            this.logger.logError("Failed to send the offer", error, peerId);
            this.failAttempt(peerId, "offer failed");
        }
    }

    async onOffer({ from, attempt, sdp }) {
        this.clearRetryTimer(from);
        this.closePeer(from, "replaced");
        this.logger.log("peer", "creating answer", from);
        let pc = null;
        try {
            pc = this.createPeer(from, attempt);
            pc.ondatachannel = ({ channel }) => this.setupChannel(from, channel);
            await pc.setRemoteDescription(sdp);
            await pc.setLocalDescription(await pc.createAnswer());
            await this.waitIceGathering(from, pc);
            if (!this.isCurrent(from, pc)) {
                return;
            }
            // Set before sending the answer, which the other device could
            // use to connect before the request returns.
            this.setConnectionTimer(from);
            const answer = pc.localDescription.toJSON();
            await this.signal({ type: "answer", to: from, attempt, sdp: answer });
        } catch (error) {
            if (pc && !this.isCurrent(from, pc)) {
                return;
            }
            this.logger.logError("Failed to send the answer", error, from);
            // The other device retries, with a new offer: else this
            // connection would stay, and its next announce would be ignored.
            this.clearRetryTimer(from);
            this.closePeer(from, "answer failed");
        }
    }

    async onAnswer({ from, attempt, sdp }) {
        const peer = this.peers.get(from);
        const pc = peer?.pc;
        let reason = null;
        if (!pc) {
            reason = "no connection";
        } else if (attempt !== peer.attempt) {
            // The answer to an offer that was replaced: it describes the
            // other device's side of a connection that no longer exists.
            reason = `old attempt (${attempt}, current ${peer.attempt})`;
        } else if (pc.signalingState !== "have-local-offer") {
            reason = `no offer pending (${pc.signalingState})`;
        }
        if (reason) {
            this.logger.log(
                "signal",
                `ignored answer from ${this.logger.shortId(from)}: ${reason}`,
                from
            );
            return;
        }
        this.setConnectionTimer(from);
        try {
            await pc.setRemoteDescription(sdp);
        } catch (error) {
            if (this.isCurrent(from, pc)) {
                this.logger.logError("Failed to apply the answer", error, from);
                this.failAttempt(from, "invalid answer");
            }
        }
    }

    // ─── Retries ──────────────────────────────────────────────────────────────

    /**
     * Gives up the attempt to connect to `peerId`, and tries again later,
     * unless it was the last attempt.
     *
     * @param {string} peerId
     * @param {string} reason - for the logs
     */
    failAttempt(peerId, reason) {
        this.closePeer(peerId, reason);
        const retry = this.getRetry(peerId);
        retry.failures++;
        if (retry.failures > RETRY_DELAYS.length) {
            this.logger.log("peer", `gave up after ${retry.failures} attempts`, peerId);
            this.resetRetries(peerId);
            return;
        }
        const delay = RETRY_DELAYS[retry.failures - 1];
        this.logger.log("peer", `${reason}, retrying in ${delay / 1000} s`, peerId);
        this.peerStates().set(peerId, "reconnecting");
        this.setRetryTimer(peerId, delay, () => this.retry(peerId));
    }

    /**
     * Gives the connection to `peerId` some time to get connected, now that
     * the offer is answered: else it could stay "connecting" forever, e.g.
     * when the devices can't reach each other, and the announces of the
     * other device would be ignored. Cleared once connected.
     */
    setConnectionTimer(peerId) {
        this.setRetryTimer(peerId, CONNECTION_TIMEOUT, () =>
            this.failAttempt(peerId, "not connected")
        );
    }

    retry(peerId) {
        if (this.id < peerId) {
            this.connect(peerId);
        } else {
            this.announceTo(peerId);
        }
    }

    getRetry(peerId) {
        if (!this.retries.has(peerId)) {
            this.retries.set(peerId, { failures: 0, timer: null });
        }
        return this.retries.get(peerId);
    }

    setRetryTimer(peerId, delay, callback) {
        const retry = this.getRetry(peerId);
        clearTimeout(retry.timer);
        retry.timer = setTimeout(() => {
            retry.timer = null;
            callback();
        }, delay);
    }

    clearRetryTimer(peerId) {
        const retry = this.retries.get(peerId);
        if (retry) {
            clearTimeout(retry.timer);
            retry.timer = null;
        }
    }

    resetRetries(peerId) {
        this.clearRetryTimer(peerId);
        this.retries.delete(peerId);
        // No more "reconnecting" for a device without a connection.
        if (!this.peers.has(peerId)) {
            this.peerStates().delete(peerId);
        }
    }

    // ─── Peers ────────────────────────────────────────────────────────────────

    /**
     * @param {string} peerId
     * @param {number} attempt - number of the offer of the connection
     */
    createPeer(peerId, attempt) {
        const pc = new RTCPeerConnection();
        pc.onconnectionstatechange = () => {
            this.peerStates().set(peerId, pc.connectionState);
            this.logger.log("state", pc.connectionState, peerId);
            if (pc.connectionState === "connected") {
                this.resetRetries(peerId);
            }
            if (pc.connectionState === "failed") {
                this.failAttempt(peerId, "failed");
            } else if (pc.connectionState === "closed") {
                this.closePeer(peerId, "closed");
            }
        };
        this.peers.set(peerId, { pc, channel: null, attempt, pingTimer: null, silenceTimer: null });
        this.peerStates().set(peerId, pc.connectionState);
        return pc;
    }

    /**
     * Whether `pc` is still the connection to `peerId`: not closed, nor
     * replaced by a new attempt.
     */
    isCurrent(peerId, pc) {
        return this.peers.get(peerId)?.pc === pc;
    }

    /**
     * Waits for the network candidates, at most `GATHERING_TIMEOUT`. A closed
     * connection never completes it: wait for the timeout.
     */
    waitIceGathering(peerId, pc) {
        if (pc.iceGatheringState === "complete") {
            return Promise.resolve();
        }
        return new Promise((resolve) => {
            const timer = setTimeout(() => {
                if (this.isCurrent(peerId, pc)) {
                    this.logger.log(
                        "peer",
                        "gathering too long, sending the candidates found",
                        peerId
                    );
                }
                resolve();
            }, GATHERING_TIMEOUT);
            pc.addEventListener("icegatheringstatechange", () => {
                if (pc.iceGatheringState === "complete") {
                    clearTimeout(timer);
                    resolve();
                }
            });
        });
    }

    setupChannel(peerId, channel) {
        const peer = this.peers.get(peerId);
        if (!peer) {
            return;
        }
        peer.channel = channel;
        channel.onopen = () => {
            this.logger.log("channel", "open", peerId);
            this.sendText(peerId, channel, `Hello world from ${this.logger.shortId(this.id)}`);
            this.startHeartbeat(peerId, channel);
        };
        channel.onmessage = ({ data }) => {
            // A message already on its way when the channel was closed, e.g.
            // its connection was replaced: it must not affect the new one.
            if (this.peers.get(peerId)?.channel !== channel) {
                return;
            }
            // Even an invalid message shows that the other device is there.
            this.resetSilenceTimer(peerId, channel);
            const message = this.parseMessage(data);
            const from = this.logger.shortId(peerId);
            if (!message) {
                // E.g. sent by another version of the PoS.
                this.logger.log("message", `ignored invalid message from ${from}`, peerId);
                return;
            }
            switch (message.type) {
                case "ping":
                    this.sendHeartbeat(peerId, channel, "pong");
                    return;
                case "pong":
                    return;
                case "bye":
                    this.closePeer(peerId, "left");
                    this.resetRetries(peerId);
                    return;
                case "text":
                    this.logger.log("message", `received "${message.text}" from ${from}`, peerId);
                    return;
                default:
                    this.logger.log(
                        "message",
                        `ignored message of type "${message.type}" from ${from}`,
                        peerId
                    );
            }
        };
        channel.onerror = ({ error }) => {
            this.logger.logError("Channel error", error, peerId);
        };
        // Without a "bye" first: the channel broke, e.g. it gave up sending a
        // message that the other device never acknowledged.
        channel.onclose = () => this.failAttempt(peerId, "channel closed");
    }

    /**
     * @param {string} data - received on a data channel
     * @returns {Object|null} the message, or null if it isn't a valid one
     */
    parseMessage(data) {
        let message;
        try {
            message = JSON.parse(data);
        } catch {
            return null;
        }
        if (typeof message?.type !== "string") {
            return null;
        }
        if (message.type === "text" && typeof message.text !== "string") {
            return null;
        }
        return message;
    }

    // ─── Heartbeat ────────────────────────────────────────────────────────────

    /**
     * Pings `peerId` regularly over `channel`, and reconnects to it if nothing
     * is received on the channel for `HEARTBEAT_TIMEOUT`. The pings and pongs
     * aren't logged: they would drown the other logs.
     */
    startHeartbeat(peerId, channel) {
        const peer = this.peers.get(peerId);
        if (peer?.channel !== channel) {
            return;
        }
        clearInterval(peer.pingTimer);
        peer.pingTimer = setInterval(
            () => this.sendHeartbeat(peerId, channel, "ping"),
            PING_INTERVAL
        );
        this.resetSilenceTimer(peerId, channel);
    }

    /**
     * Restarts the time given to `peerId` to send something on `channel`.
     */
    resetSilenceTimer(peerId, channel) {
        const peer = this.peers.get(peerId);
        if (peer?.channel !== channel) {
            return;
        }
        clearTimeout(peer.silenceTimer);
        peer.silenceTimer = setTimeout(() => {
            if (this.peers.get(peerId)?.channel === channel) {
                this.failAttempt(peerId, "no heartbeat");
            }
        }, HEARTBEAT_TIMEOUT);
    }

    /**
     * @param {string} peerId
     * @param {RTCDataChannel} channel
     * @param {"ping"|"pong"} type
     */
    sendHeartbeat(peerId, channel, type) {
        if (channel.readyState !== "open") {
            return;
        }
        try {
            channel.send(JSON.stringify({ type }));
        } catch (error) {
            this.logger.logError(`Failed to send a ${type}`, error, peerId);
        }
    }

    stopHeartbeat(peer) {
        clearInterval(peer.pingTimer);
        clearTimeout(peer.silenceTimer);
        peer.pingTimer = null;
        peer.silenceTimer = null;
    }

    /**
     * @param {string} peerId
     * @param {string} reason - for the logs
     */
    closePeer(peerId, reason) {
        const peer = this.peers.get(peerId);
        if (!peer) {
            return;
        }
        this.logger.log("peer", `closed: ${reason}`, peerId);
        this.peers.delete(peerId);
        this.peerStates().delete(peerId);
        this.stopHeartbeat(peer);
        peer.pc.onconnectionstatechange = null;
        if (peer.channel) {
            peer.channel.onclose = null;
            peer.channel.onerror = null;
            peer.channel.close();
        }
        peer.pc.close();
    }
}

services.add(WebRtcPlugin);

/**
 * @returns {WebRtcPlugin}
 */
export function useWebRtc() {
    return usePlugin(WebRtcPlugin);
}
