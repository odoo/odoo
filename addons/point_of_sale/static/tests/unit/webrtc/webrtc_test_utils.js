import { expect } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, runAllTimers, waitUntil } from "@odoo/hoot-dom";
import { MockServer, makeServerError, onRpc } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { waitForChannels } from "@bus/../tests/bus_test_helpers";
import { WEBSOCKET_CLOSE_CODES } from "@bus/workers/websocket_worker";
import {
    WebRtcPlugin,
    webrtcChannel,
    webrtcSignalType,
} from "@point_of_sale/app/webrtc/webrtc_plugin";
import { WebRtcLogPlugin } from "@point_of_sale/app/webrtc/webrtc_log_plugin";
import { setupPosEnv } from "../utils";

// Helpers of the WebRTC unit tests. The device under test runs the real
// plugin, on the real bus (mock websocket), with a fake RTCPeerConnection. The
// other devices are simulated: their signaling messages are sent on the bus.

export const T1 = "device1";
export const T2 = "device2";
export const T3 = "device3";

// ----- Fake WebRTC ----- //

export class FakeDataChannel {
    readyState = "connecting";
    onopen = null;
    onmessage = null;
    onerror = null;
    onclose = null;
    /** @type {Object[]} messages sent, parsed, heartbeat included */
    sent = [];
    /**
     * Whether the other device answers the pings. Set it to false for a
     * device that stopped answering (crashed, frozen, network down).
     */
    answerPings = true;

    /**
     * Like the real one: fails unless the channel is open.
     *
     * The pong is received at once, during the `send` of the ping: on the
     * mocked clock, the timers that are due run one after the other, without
     * the promises in between, so a pong received later would always come
     * after the end of the heartbeat timeout.
     */
    send(data) {
        if (this.readyState !== "open") {
            throw new DOMException("The data channel is not open.", "InvalidStateError");
        }
        const message = JSON.parse(data);
        this.sent.push(message);
        if (message.type === "ping" && this.answerPings) {
            this.receive({ type: "pong" });
        }
    }

    /** Messages sent, without the heartbeat (pings and pongs). */
    get messages() {
        return this.sent.filter((message) => !["ping", "pong"].includes(message.type));
    }

    /** Number of pings sent. */
    get pings() {
        return this.sent.filter((message) => message.type === "ping").length;
    }

    close() {
        this.readyState = "closed";
    }

    /** Simulates the channel opening (both sides connected). */
    open() {
        this.readyState = "open";
        this.onopen?.();
    }

    /**
     * Simulates a message sent by the other device. Like a message already
     * on its way when the channel closes, it is received even once closed.
     */
    receive(message) {
        this.receiveRaw(JSON.stringify(message));
    }

    /** Simulates data sent by the other device, valid or not. */
    receiveRaw(data) {
        this.onmessage?.({ data });
    }

    /** Simulates the channel closed by the other side, or broken. */
    closeFromOtherSide() {
        this.readyState = "closed";
        this.onclose?.();
    }
}

/**
 * A peer connection that never touches the network: the descriptions are fake,
 * the ICE gathering completes at once (unless `holdIceGathering`), and the test
 * decides of the connection state (`setConnectionState`).
 *
 * Like the real one, once closed, its methods fail and it fires no event.
 */
export class FakeRTCPeerConnection {
    /** When true, the ICE gathering waits for `completeIceGathering`. */
    static holdIceGathering = false;

    connectionState = "new";
    signalingState = "stable";
    iceGatheringState = "new";
    localDescription = null;
    remoteDescription = null;
    onconnectionstatechange = null;
    ondatachannel = null;
    /** @type {FakeDataChannel|null} channel created by this side */
    channel = null;
    closed = false;
    iceGatheringListeners = [];

    createDataChannel() {
        this.checkNotClosed();
        this.channel = new FakeDataChannel();
        return this.channel;
    }

    async createOffer() {
        this.checkNotClosed();
        return { type: "offer", sdp: "fake offer" };
    }

    async createAnswer() {
        this.checkNotClosed();
        return { type: "answer", sdp: "fake answer" };
    }

    async setLocalDescription(description) {
        this.checkNotClosed();
        this.localDescription = { ...description, toJSON: () => ({ ...description }) };
        this.signalingState = description.type === "offer" ? "have-local-offer" : "stable";
        this.iceGatheringState = FakeRTCPeerConnection.holdIceGathering ? "gathering" : "complete";
    }

    async setRemoteDescription(description) {
        this.checkNotClosed();
        this.remoteDescription = description;
        this.signalingState = description.type === "offer" ? "have-remote-offer" : "stable";
    }

    addEventListener(type, listener) {
        if (type === "icegatheringstatechange") {
            this.iceGatheringListeners.push(listener);
        }
    }

    checkNotClosed() {
        if (this.closed) {
            throw new DOMException("The peer connection is closed.", "InvalidStateError");
        }
    }

    /** Ends a gathering held by `holdIceGathering`. Nothing happens once closed. */
    completeIceGathering() {
        if (this.closed) {
            return;
        }
        this.iceGatheringState = "complete";
        for (const listener of this.iceGatheringListeners) {
            listener();
        }
    }

    /** Like the real one: closing doesn't trigger `onconnectionstatechange`. */
    close() {
        this.closed = true;
        this.connectionState = "closed";
        this.signalingState = "closed";
    }

    setConnectionState(state) {
        this.connectionState = state;
        this.onconnectionstatechange?.();
    }
}

// ----- Setup ----- //

/** Signaling messages sent by the device under test, in order. */
let sentMessages = [];

/**
 * Prepares the device under test, before `setupPosEnv` starts it:
 * - its id is `id`, so that the tests know which device sends the offer;
 * - `RTCPeerConnection` is fake;
 * - the signaling route relays the messages on the bus, like the server, and
 *   adds a step per message relayed (e.g. "offer to device2", "announce to
 *   all"), see also `lastSent`. While `server.reachable` is false, it fails and
 *   relays nothing. While `server.error` is set, it fails with this error.
 *   While `server.held` is a promise, it waits for it before answering
 *   (`server.waiting` counts the requests waiting);
 * - the errors are only kept in the logs: `console.error` would fail the test.
 *
 * @param {Object} [params]
 * @param {string|null} [params.id] - id of the device under test (null: a real one)
 * @returns {{ server: {
 *  reachable: boolean,
 *  error: Error|null,
 *  held: Promise|null,
 *  waiting: number,
 * } }}
 */
export function setupWebrtc({ id = T1 } = {}) {
    const server = { reachable: true, error: null, held: null, waiting: 0 };
    sentMessages = [];
    // `id: null`: the device builds its ids as in real life.
    if (id) {
        patch(WebRtcPlugin.prototype, {
            newId: () => id,
        });
    }
    patch(WebRtcLogPlugin.prototype, {
        logError(text, error, peer = null) {
            this.add("error", `${text}: ${error?.message || error}`, peer);
        },
    });
    patch(window, { RTCPeerConnection: FakeRTCPeerConnection });
    onRpc("/pos/webrtc/signal", async (request) => {
        if (server.held) {
            server.waiting++;
            await server.held;
            server.waiting--;
        }
        if (server.error) {
            throw server.error;
        }
        if (!server.reachable) {
            throw makeServerError({ message: "Server unreachable" });
        }
        const { params } = await request.json();
        const { message } = params;
        expect.step(`${message.type} to ${message.to || "all"}`);
        sentMessages.push(message);
        sendOnBus(message);
        return true;
    });
    return { server };
}

/**
 * The ICE gathering of the peer connections waits for `completeIceGathering`.
 */
export function holdIceGathering() {
    patch(FakeRTCPeerConnection, { holdIceGathering: true });
}

/**
 * @param {string} type
 * @returns {Object|undefined} last signaling message of that type sent by the
 *  device under test
 */
export function lastSent(type) {
    return sentMessages.findLast((message) => message.type === type);
}

/**
 * Starts the PoS, and waits for the device to listen to the bus: before, the
 * signaling messages of the other devices don't reach it, and the websocket
 * can't be dropped.
 */
export async function startDevice() {
    const store = await setupPosEnv();
    // Without WebRTC, the plugin doesn't listen to its channel.
    await waitForChannels(
        window.RTCPeerConnection ? [webrtcChannel(odoo.pos_config_id)] : [odoo.access_token]
    );
    return store;
}

/**
 * Sends a signaling message on the bus, like the server, without waiting for
 * the device under test to receive it (see `receiveSignal`).
 */
export function sendOnBus(message) {
    // The mock server gives the channel as asked: who may get it is tested
    // on the real server.
    const configId = odoo.pos_config_id;
    MockServer.env["bus.bus"]._sendone(
        webrtcChannel(configId),
        webrtcSignalType(configId),
        message
    );
}

// ----- Other devices ----- //

/**
 * Sends a signaling message from another device, and waits for the device
 * under test to receive it.
 */
export async function receiveSignal(webrtc, message) {
    const from = webrtc.logger.shortId(message.from);
    const text = `received ${message.type} from ${from}${message.to ? "" : " to all"}`;
    const count = countLogs(webrtc, text);
    sendOnBus(message);
    await waitUntil(() => countLogs(webrtc, text) > count);
}

function countLogs(webrtc, text) {
    return webrtc.logger.logs().filter((log) => log.text === text).length;
}

/**
 * The other device answers `offer`, sent by the device under test.
 */
export async function receiveAnswer(webrtc, offer, sdp = "fake answer") {
    await receiveSignal(webrtc, {
        type: "answer",
        from: offer.to,
        to: offer.from,
        attempt: offer.attempt,
        sdp: { type: "answer", sdp },
    });
}

/**
 * @param {Object} webrtc
 * @returns {string[]} texts of the errors logged
 */
export function loggedErrors(webrtc) {
    return webrtc.logger
        .logs()
        .filter((log) => log.type === "error")
        .map((log) => log.text);
}

/**
 * Connects the device under test to `peerId`, a bigger id: the other device
 * announces itself, the device under test sends the offer, receives the
 * answer, and the connection and its data channel open.
 *
 * @returns {Promise<FakeRTCPeerConnection>}
 */
export async function connectTo(webrtc, peerId) {
    await receiveSignal(webrtc, { type: "announce", from: peerId });
    await waitUntil(() => webrtc.peers.get(peerId)?.pc.signalingState === "have-local-offer");
    return acceptOffer(webrtc, peerId);
}

/**
 * The other device answers the last offer sent to it, and the connection and
 * its data channel open.
 *
 * @returns {Promise<FakeRTCPeerConnection>}
 */
export async function acceptOffer(webrtc, peerId) {
    const { pc } = webrtc.peers.get(peerId);
    await receiveAnswer(webrtc, lastSent("offer"));
    await waitUntil(() => pc.signalingState === "stable");
    pc.setConnectionState("connected");
    pc.channel.open();
    return pc;
}

/**
 * Connects the device under test to `peerId`, a smaller id: the other
 * device sends an offer, the device under test answers, and the connection
 * and the data channel created by the other device open.
 *
 * @param {Object} webrtc
 * @param {string} peerId
 * @param {Object} [params]
 * @param {number} [params.attempt] - number of the offer of the other device
 * @returns {Promise<FakeRTCPeerConnection>}
 */
export async function connectFrom(webrtc, peerId, { attempt = 1 } = {}) {
    await receiveSignal(webrtc, {
        type: "offer",
        from: peerId,
        to: webrtc.id,
        attempt,
        sdp: { type: "offer", sdp: "fake offer" },
    });
    await waitUntil(() => {
        const answer = lastSent("answer");
        return answer?.to === peerId && answer.attempt === attempt;
    });
    const { pc } = webrtc.peers.get(peerId);
    const channel = new FakeDataChannel();
    pc.ondatachannel({ channel });
    pc.setConnectionState("connected");
    channel.open();
    return pc;
}

// ----- Bus ----- //

/**
 * The websocket is closed abnormally (server restarted, network cut), and the
 * bus reconnects: `BUS:RECONNECT`.
 */
export async function dropWebsocket() {
    MockServer.env["bus.bus"]._simulateDisconnection(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
    await runAllTimers();
}

/**
 * The device goes offline then online again (sleep, Wi-Fi): the bus stops,
 * then starts again: `BUS:CONNECT`.
 */
export async function goOfflineThenOnline() {
    patch(navigator, { onLine: false });
    await manuallyDispatchProgrammaticEvent(window, "offline");
    patch(navigator, { onLine: true });
    await manuallyDispatchProgrammaticEvent(window, "online");
    await runAllTimers();
}
