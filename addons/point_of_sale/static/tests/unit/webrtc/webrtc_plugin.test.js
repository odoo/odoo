import { describe, expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { runAllTimers, waitUntil } from "@odoo/hoot-dom";
import { makeServerError } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import {
    addBusServiceListeners,
    lockWebsocketConnect,
    waitForChannels,
} from "@bus/../tests/bus_test_helpers";
import { webrtcChannel, webrtcSignalType } from "@point_of_sale/app/webrtc/webrtc_plugin";
import { definePosModels } from "../data/generate_model_definitions";
import { setupPosEnv } from "../utils";
import {
    FakeDataChannel,
    FakeRTCPeerConnection,
    T1,
    T2,
    T3,
    acceptOffer,
    connectFrom,
    connectTo,
    dropWebsocket,
    goOfflineThenOnline,
    holdIceGathering,
    lastSent,
    loggedErrors,
    receiveAnswer,
    receiveSignal,
    sendOnBus,
    setupWebrtc,
    startDevice,
} from "./webrtc_test_utils";

// The device under test is T1 (the smaller id, it sends the offers), or T2
// with `setupWebrtc({ id: T2 })` (the bigger id, it answers). The steps are the
// signaling messages it sends, e.g. "offer to device2".

definePosModels();

// Time given to the other device to answer an offer, or to send an
// offer after an announce.
const ANSWER_TIMEOUT = 15000;
// Time given to the gathering of the candidates.
const GATHERING_TIMEOUT = 5000;
// Delays before the attempts 2 to 5, then it gives up.
const RETRY_DELAYS = [1000, 2000, 4000, 8000];
// Time given to a connection to get connected once the offer is answered.
const CONNECTION_TIMEOUT = 15000;
// A device pings the other ones this often over the data channel...
const PING_INTERVAL = 10000;
// ... and closes the connection to one it heard nothing from for this long.
const HEARTBEAT_TIMEOUT = 30000;
// The mocked time also flows for real: a timer started a few milliseconds
// ago fires a few milliseconds earlier. Check that nothing happens until
// `MARGIN` before the end of a delay, then that it happens at the end.
const MARGIN = 500;

describe("announcing again", () => {
    test("announces itself once when it starts", async () => {
        // The first connection of the websocket is not a reconnection.
        addBusServiceListeners(["BUS:CONNECT", () => expect.step("BUS:CONNECT")]);
        setupWebrtc();
        await setupPosEnv();
        await expect.waitForSteps(["announce to all", "BUS:CONNECT"], { ignoreOrder: true });
        // Nothing else, ever.
        await runAllTimers();
        expect.verifySteps([]);
    });

    test("announces itself again when the websocket reconnects", async () => {
        // E.g. the server restarted: the other devices may have missed it.
        setupWebrtc();
        await startDevice();
        await expect.waitForSteps(["announce to all"]);
        await dropWebsocket();
        await expect.waitForSteps(["announce to all"]);
    });

    test("announces itself again when back online", async () => {
        // The bus stops when the device goes offline, and starts again when
        // it is back online: a new connection, not a reconnection.
        setupWebrtc();
        await startDevice();
        await expect.waitForSteps(["announce to all"]);
        await goOfflineThenOnline();
        await expect.waitForSteps(["announce to all"]);
    });

    test("keeps its connections when the websocket reconnects", async () => {
        // The connections between devices don't use the server: when the
        // server restarts, both devices announce themselves again, and
        // nothing else happens.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        // T1's websocket reconnects: it announces itself again.
        await dropWebsocket();
        await expect.waitForSteps(["announce to all"]);
        // T2's too: its announce is ignored.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await runAllTimers();
        expect.verifySteps([]);
        // Same connection, still connected.
        expect(webrtc.peers.get(T2).pc).toBe(pc);
        expect(pc.closed).toBe(false);
        expect(webrtc.peerStates().get(T2)).toBe("connected");
    });

    test("announces itself once the server is reachable, if it couldn't when it started", async () => {
        // Nobody knows a device whose announce failed: it would stay alone.
        // The websocket can't connect: don't wait for the bus (`startDevice`).
        const { server } = setupWebrtc();
        server.reachable = false;
        const unlockWebsocket = lockWebsocketConnect();
        const { webrtc } = await setupPosEnv();
        // The announce fails.
        await waitUntil(() =>
            webrtc.logger.logs().some((log) => log.text.startsWith("Failed to announce"))
        );
        // The websocket fails to connect, and retries.
        await runAllTimers();
        expect.verifySteps([]);
        // The server is back: the websocket connects, and T1 announces itself.
        server.reachable = true;
        unlockWebsocket();
        await runAllTimers();
        await expect.waitForSteps(["announce to all"]);
    });
});

describe("signaling races", () => {
    for (const replyFirst of [false, true]) {
        const order = replyFirst ? "reply first" : "announce first";
        test(`two devices announce at the same time: smaller id (${order})`, async () => {
            // Both devices start at the same time: the other one gets the
            // announce of the device under test and replies with its own,
            // on top of its own announce to all. Only one offer is sent, and
            // the second announce doesn't replace the connection in progress.
            // The reply can overtake the announce to all if its request is slow.
            setupWebrtc();
            const { webrtc } = await startDevice();
            await expect.waitForSteps(["announce to all"]);
            // T2's announce to all, and its reply to T1's announce.
            const announces = [
                { type: "announce", from: T2 },
                { type: "announce", from: T2, to: T1 },
            ];
            if (replyFirst) {
                announces.reverse();
            }
            // First announce: T1 sends the offer.
            await receiveSignal(webrtc, announces[0]);
            await expect.waitForSteps([`offer to ${T2}`]);
            const { pc } = webrtc.peers.get(T2);
            // Second announce: ignored, no second offer.
            await receiveSignal(webrtc, announces[1]);
            // Less than the time given to the answer.
            await advanceTime(1000);
            expect.verifySteps([]);
            expect(webrtc.peers.get(T2).pc).toBe(pc);
            expect(pc.closed).toBe(false);
            // T2 answers: connected.
            await receiveAnswer(webrtc, lastSent("offer"));
            await waitUntil(() => pc.signalingState === "stable");
            pc.setConnectionState("connected");
            pc.channel.open();
            expect(webrtc.peers.size).toBe(1);
            expect(webrtc.peerStates().get(T2)).toBe("connected");
            expect(pc.channel.messages).toEqual([{ type: "text", text: `Hello world from ${T1}` }]);
            // Nothing else, ever.
            await runAllTimers();
            expect.verifySteps([]);
        });
    }

    test("two devices announce at the same time: bigger id", async () => {
        // The device under test replies to the announce of the smaller id
        // and lets it send the offer: it never sends one itself.
        setupWebrtc({ id: T2 });
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T1 announces itself: T2 replies with an announce, not an offer.
        await receiveSignal(webrtc, { type: "announce", from: T1 });
        await expect.waitForSteps([`announce to ${T1}`]);
        // T1 sends the offer: T2 answers.
        await receiveSignal(webrtc, {
            type: "offer",
            from: T1,
            to: T2,
            sdp: { type: "offer", sdp: "fake offer" },
        });
        await expect.waitForSteps([`answer to ${T1}`]);
        // The channel created by T1 opens: connected.
        const { pc } = webrtc.peers.get(T1);
        const channel = new FakeDataChannel();
        pc.ondatachannel({ channel });
        pc.setConnectionState("connected");
        channel.open();
        expect(webrtc.peers.size).toBe(1);
        expect(webrtc.peerStates().get(T1)).toBe("connected");
        expect(channel.messages).toEqual([{ type: "text", text: `Hello world from ${T2}` }]);
        // Nothing else, ever.
        await runAllTimers();
        expect.verifySteps([]);
    });

    test("ignores the answer to an attempt that was replaced", async () => {
        // An attempt can be replaced while its answer is on the way, e.g. it
        // is retried because the answer took too long (simulated here with a
        // direct call). The late answer must not be applied to the new
        // connection: it describes the connection of the old offer.
        setupWebrtc();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // First attempt: T2 announces itself, T1 sends an offer.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await expect.waitForSteps([`offer to ${T2}`]);
        const oldOffer = lastSent("offer");
        // Second attempt, before any answer: a new offer.
        webrtc.connect(T2);
        await expect.waitForSteps([`offer to ${T2}`]);
        const newOffer = lastSent("offer");
        expect(newOffer.attempt).not.toBe(oldOffer.attempt);
        const { pc } = webrtc.peers.get(T2);
        // The answer to the first offer arrives: ignored.
        await receiveAnswer(webrtc, oldOffer, "old answer");
        // Less than the time given to the answer.
        await advanceTime(1000);
        expect(pc.signalingState).toBe("have-local-offer");
        expect(pc.remoteDescription).toBe(null);
        // The answer to the second offer arrives: applied, connected.
        await receiveAnswer(webrtc, newOffer, "new answer");
        await waitUntil(() => pc.signalingState === "stable");
        expect(pc.remoteDescription.sdp).toBe("new answer");
        pc.setConnectionState("connected");
        pc.channel.open();
        expect(webrtc.peerStates().get(T2)).toBe("connected");
        expect(pc.channel.messages).toEqual([{ type: "text", text: `Hello world from ${T1}` }]);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("sends no offer when the peer is closed while gathering candidates", async () => {
        // E.g. the page is hidden while the offer is prepared.
        setupWebrtc();
        holdIceGathering();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T2 announces itself: T1 prepares its offer, and gathers candidates.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await waitUntil(() => webrtc.peers.get(T2)?.pc.iceGatheringState === "gathering");
        const { pc } = webrtc.peers.get(T2);
        // The page is hidden meanwhile: the connection closes.
        webrtc.stop("pagehide");
        // The gathering ends (or times out): no offer, no error.
        pc.completeIceGathering();
        await runAllTimers();
        expect.verifySteps([]);
        expect(webrtc.peers.size).toBe(0);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("sends no answer when the peer is closed while gathering candidates", async () => {
        setupWebrtc({ id: T2 });
        holdIceGathering();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T1 sends an offer: T2 prepares its answer, and gathers candidates.
        await receiveSignal(webrtc, {
            type: "offer",
            from: T1,
            to: T2,
            attempt: 1,
            sdp: { type: "offer", sdp: "fake offer" },
        });
        await waitUntil(() => webrtc.peers.get(T1)?.pc.iceGatheringState === "gathering");
        const { pc } = webrtc.peers.get(T1);
        // The page is hidden meanwhile: the connection closes.
        webrtc.stop("pagehide");
        // The gathering ends (or times out): no answer, no error.
        pc.completeIceGathering();
        await runAllTimers();
        expect.verifySteps([]);
        expect(webrtc.peers.size).toBe(0);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("answers only the last of two offers received back to back", async () => {
        // The second offer arrives while the answer to the first one is
        // prepared: the first connection is replaced, and its answer is never
        // sent. The answer says which offer it answers.
        setupWebrtc({ id: T2 });
        holdIceGathering();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        const offer = (attempt) => ({
            type: "offer",
            from: T1,
            to: T2,
            attempt,
            sdp: { type: "offer", sdp: `offer ${attempt}` },
        });
        // Offer 1: T2 prepares its answer, and gathers candidates.
        await receiveSignal(webrtc, offer(1));
        await waitUntil(() => webrtc.peers.get(T1)?.pc.iceGatheringState === "gathering");
        const oldPc = webrtc.peers.get(T1).pc;
        // Offer 2, meanwhile: a new connection replaces the first one.
        await receiveSignal(webrtc, offer(2));
        await waitUntil(() => webrtc.peers.get(T1)?.pc.iceGatheringState === "gathering");
        const { pc } = webrtc.peers.get(T1);
        expect(pc).not.toBe(oldPc);
        expect(oldPc.closed).toBe(true);
        // Both gatherings end: a single answer, to offer 2.
        oldPc.completeIceGathering();
        pc.completeIceGathering();
        await expect.waitForSteps([`answer to ${T1}`]);
        pc.setConnectionState("connected");
        await runAllTimers();
        expect.verifySteps([]);
        expect(lastSent("answer").attempt).toBe(2);
        expect(pc.remoteDescription.sdp).toBe("offer 2");
        expect(webrtc.peers.size).toBe(1);
        expect(loggedErrors(webrtc)).toEqual([]);
    });
});

describe("lost signaling and timeouts", () => {
    test("retries when the answer never comes back", async () => {
        // The offer or the answer is lost on the way (server restarted,
        // websocket reconnecting...).
        setupWebrtc();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T2 announces itself: T1 sends an offer, never answered.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await expect.waitForSteps([`offer to ${T2}`]);
        const { pc: oldPc } = webrtc.peers.get(T2);
        // No answer for 15 s: the attempt is closed.
        await advanceTime(ANSWER_TIMEOUT - MARGIN);
        expect(oldPc.closed).toBe(false);
        await advanceTime(MARGIN);
        expect(oldPc.closed).toBe(true);
        expect(webrtc.peers.has(T2)).toBe(false);
        // 1 s later: a new offer.
        await advanceTime(RETRY_DELAYS[0]);
        await expect.waitForSteps([`offer to ${T2}`]);
        // T2 answers it: connected.
        const { pc } = webrtc.peers.get(T2);
        await receiveAnswer(webrtc, lastSent("offer"));
        await waitUntil(() => pc.signalingState === "stable");
        pc.setConnectionState("connected");
        pc.channel.open();
        expect(webrtc.peerStates().get(T2)).toBe("connected");
        // No more retries.
        await runAllTimers();
        expect.verifySteps([]);
        expect(webrtc.peers.get(T2).pc).toBe(pc);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("waits longer before each retry, and gives up after 5 attempts", async () => {
        // E.g. the other device crashed without saying it leaves: don't
        // send it offers forever. If it is still there, its next announce
        // starts again.
        setupWebrtc();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T2 announces itself: offer 1, never answered.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await expect.waitForSteps([`offer to ${T2}`]);
        // Offers 2 to 5: each one 15 s + 1, 2, 4, 8 s after the previous one.
        for (const delay of RETRY_DELAYS) {
            await advanceTime(ANSWER_TIMEOUT + delay - MARGIN);
            expect.verifySteps([]);
            await advanceTime(MARGIN);
            await expect.waitForSteps([`offer to ${T2}`]);
        }
        // Offer 5 isn't answered either: T1 gives up.
        await advanceTime(ANSWER_TIMEOUT);
        await runAllTimers();
        expect.verifySteps([]);
        expect(webrtc.peers.size).toBe(0);
        // T2 announces itself again: T1 tries again.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await expect.waitForSteps([`offer to ${T2}`]);
    });

    test("announces itself again when its reply to an announce gets no offer", async () => {
        // The device with the bigger id replies to the announce of the
        // newcomer and waits for its offer: the reply can be lost too.
        setupWebrtc({ id: T2 });
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T1 announces itself: T2 replies, and gets no offer.
        await receiveSignal(webrtc, { type: "announce", from: T1 });
        await expect.waitForSteps([`announce to ${T1}`]);
        // 15 s + 1 s later: T2 replies again.
        await advanceTime(ANSWER_TIMEOUT + RETRY_DELAYS[0] - MARGIN);
        expect.verifySteps([]);
        await advanceTime(MARGIN);
        await expect.waitForSteps([`announce to ${T1}`]);
        // T1 sends its offer: T2 answers.
        await receiveSignal(webrtc, {
            type: "offer",
            from: T1,
            to: T2,
            attempt: 1,
            sdp: { type: "offer", sdp: "fake offer" },
        });
        await expect.waitForSteps([`answer to ${T1}`]);
        webrtc.peers.get(T1).pc.setConnectionState("connected");
        // No more announces.
        await runAllTimers();
        expect.verifySteps([]);
        expect(webrtc.peers.size).toBe(1);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("stops announcing itself to a device that never sends an offer", async () => {
        setupWebrtc({ id: T2 });
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T1 announces itself: T2 replies (1), and gets no offer.
        await receiveSignal(webrtc, { type: "announce", from: T1 });
        await expect.waitForSteps([`announce to ${T1}`]);
        // Replies 2 to 5: each one 15 s + 1, 2, 4, 8 s after the previous one.
        for (const delay of RETRY_DELAYS) {
            await advanceTime(ANSWER_TIMEOUT + delay);
            await expect.waitForSteps([`announce to ${T1}`]);
        }
        // Then T2 gives up.
        await runAllTimers();
        expect.verifySteps([]);
    });

    test("sends the offer with the candidates gathered so far when the gathering is too long", async () => {
        setupWebrtc();
        holdIceGathering();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T2 announces itself: T1 prepares its offer, the gathering never ends.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await waitUntil(() => webrtc.peers.get(T2)?.pc.iceGatheringState === "gathering");
        // 5 s later: the offer is sent anyway.
        await advanceTime(GATHERING_TIMEOUT - MARGIN);
        expect.verifySteps([]);
        await advanceTime(MARGIN);
        await expect.waitForSteps([`offer to ${T2}`]);
        expect(lastSent("offer").sdp).toEqual({ type: "offer", sdp: "fake offer" });
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("sends the answer with the candidates gathered so far when the gathering is too long", async () => {
        setupWebrtc({ id: T2 });
        holdIceGathering();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T1 sends an offer: T2 prepares its answer, the gathering never ends.
        await receiveSignal(webrtc, {
            type: "offer",
            from: T1,
            to: T2,
            attempt: 1,
            sdp: { type: "offer", sdp: "fake offer" },
        });
        await waitUntil(() => webrtc.peers.get(T1)?.pc.iceGatheringState === "gathering");
        // 5 s later: the answer is sent anyway.
        await advanceTime(GATHERING_TIMEOUT - MARGIN);
        expect.verifySteps([]);
        await advanceTime(MARGIN);
        await expect.waitForSteps([`answer to ${T1}`]);
        expect(lastSent("answer").attempt).toBe(1);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("closes the connection and retries when the answer can't be applied", async () => {
        setupWebrtc();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T2 announces itself: T1 sends an offer.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await expect.waitForSteps([`offer to ${T2}`]);
        // T2's answer is invalid: error logged, the connection closes.
        const { pc: oldPc } = webrtc.peers.get(T2);
        oldPc.setRemoteDescription = async () => {
            throw new Error("invalid answer");
        };
        await receiveAnswer(webrtc, lastSent("offer"));
        await waitUntil(() => oldPc.closed);
        expect(webrtc.peers.has(T2)).toBe(false);
        expect(loggedErrors(webrtc)).toEqual(["Failed to apply the answer: invalid answer"]);
        // 1 s later: a new offer.
        await advanceTime(RETRY_DELAYS[0]);
        await expect.waitForSteps([`offer to ${T2}`]);
        // T2 answers it: connected.
        const { pc } = webrtc.peers.get(T2);
        await receiveAnswer(webrtc, lastSent("offer"));
        await waitUntil(() => pc.signalingState === "stable");
        pc.setConnectionState("connected");
        expect(webrtc.peerStates().get(T2)).toBe("connected");
    });

    test("closes the connection when the offer can't be applied", async () => {
        // The other device retries: the connection must not stay, else its
        // next announce would be ignored.
        setupWebrtc({ id: T2 });
        // Every offer is invalid.
        patch(FakeRTCPeerConnection.prototype, {
            async setRemoteDescription() {
                throw new Error("invalid offer");
            },
        });
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        // T1 sends an offer: error logged, no answer, the connection closes.
        await receiveSignal(webrtc, {
            type: "offer",
            from: T1,
            to: T2,
            attempt: 1,
            sdp: { type: "offer", sdp: "fake offer" },
        });
        await waitUntil(() => loggedErrors(webrtc).length);
        expect(loggedErrors(webrtc)).toEqual(["Failed to send the answer: invalid offer"]);
        expect(webrtc.peers.size).toBe(0);
        // T1 announces itself again: not ignored, T2 replies.
        await receiveSignal(webrtc, { type: "announce", from: T1 });
        await expect.waitForSteps([`announce to ${T1}`]);
    });
});

describe("network hiccup", () => {
    // A short cut of the network between the devices (Wi-Fi roaming, cable
    // unplugged and plugged back): the browser sets the connection to
    // "disconnected", and back to "connected" if the network comes back in
    // time, on its own. Meanwhile the data channel stays open. Shorter than
    // the time after which a silent device is considered gone.
    const HICCUP = 5000;

    for (const id of [T1, T2]) {
        const side = id === T1 ? "smaller id" : "bigger id";
        const peerId = id === T1 ? T2 : T1;
        test(`keeps the connection through a short network hiccup (${side})`, async () => {
            setupWebrtc({ id });
            const { webrtc } = await startDevice();
            const pc =
                id === T1 ? await connectTo(webrtc, peerId) : await connectFrom(webrtc, peerId);
            const sent = id === T1 ? `offer to ${peerId}` : `answer to ${peerId}`;
            await expect.waitForSteps(["announce to all", sent]);
            // The network is cut: the other device doesn't answer the pings
            // anymore. The connection is kept, and shown as disconnected.
            const { channel } = webrtc.peers.get(peerId);
            channel.answerPings = false;
            pc.setConnectionState("disconnected");
            await advanceTime(HICCUP);
            expect.verifySteps([]);
            expect(webrtc.peers.get(peerId).pc).toBe(pc);
            expect(pc.closed).toBe(false);
            expect(webrtc.peerStates().get(peerId)).toBe("disconnected");
            // The network is back: same connection, connected again.
            channel.answerPings = true;
            pc.setConnectionState("connected");
            expect(webrtc.peerStates().get(peerId)).toBe("connected");
            // Nothing else, ever.
            await runAllTimers();
            expect.verifySteps([]);
            expect(webrtc.peers.get(peerId).pc).toBe(pc);
            expect(pc.closed).toBe(false);
            expect(loggedErrors(webrtc)).toEqual([]);
        });
    }

    test("keeps sending messages while disconnected", async () => {
        // The data channel stays open: the browser keeps the messages and
        // delivers them once the network is back.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        const { channel } = webrtc.peers.get(T2);
        pc.setConnectionState("disconnected");
        webrtc.broadcast("Hi");
        expect(channel.messages).toEqual([
            { type: "text", text: `Hello world from ${T1}` },
            { type: "text", text: "Hi" },
        ]);
        // The network is back: the channel didn't reopen, nothing is sent
        // again.
        pc.setConnectionState("connected");
        await runAllTimers();
        expect(channel.messages).toEqual([
            { type: "text", text: `Hello world from ${T1}` },
            { type: "text", text: "Hi" },
        ]);
        expect.verifySteps([]);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("keeps a disconnected connection when both devices announce themselves again", async () => {
        // The network cut also drops the websockets: when they reconnect,
        // both devices announce themselves again, while their connection is
        // still disconnected. The browser restores it on its own: rebuilding
        // it would only make the hiccup longer.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        pc.setConnectionState("disconnected");
        // T1's websocket reconnects: it announces itself again.
        await dropWebsocket();
        await expect.waitForSteps(["announce to all"]);
        // T2's too: its announce is ignored.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        expect.verifySteps([]);
        expect(webrtc.peers.get(T2).pc).toBe(pc);
        expect(pc.closed).toBe(false);
        // The network is back: same connection, connected again.
        pc.setConnectionState("connected");
        await runAllTimers();
        expect.verifySteps([]);
        expect(webrtc.peers.get(T2).pc).toBe(pc);
        expect(webrtc.peerStates().get(T2)).toBe("connected");
        expect(loggedErrors(webrtc)).toEqual([]);
    });
});

describe("failure and reconnection", () => {
    // The browser sets a connection to "failed" when the other device stops
    // answering (network down for too long, other device asleep or crashed).
    // The connection is rebuilt from scratch: same retries as when it is set up
    // (see "lost signaling and timeouts"), and still only the smaller id sends
    // offers.

    test("reconnects with a new connection when the connection fails (smaller id)", async () => {
        setupWebrtc();
        const { webrtc } = await startDevice();
        const oldPc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        // The connection fails: closed at once.
        oldPc.setConnectionState("failed");
        expect(oldPc.closed).toBe(true);
        expect(webrtc.peers.has(T2)).toBe(false);
        // 1 s later: a new offer.
        await advanceTime(RETRY_DELAYS[0] - MARGIN);
        expect.verifySteps([]);
        await advanceTime(MARGIN);
        await expect.waitForSteps([`offer to ${T2}`]);
        // T2 answers it: connected again, on a new connection.
        const pc = await acceptOffer(webrtc, T2);
        expect(pc).not.toBe(oldPc);
        expect(webrtc.peerStates().get(T2)).toBe("connected");
        expect(pc.channel.messages).toEqual([{ type: "text", text: `Hello world from ${T1}` }]);
        // Nothing else, ever.
        await runAllTimers();
        expect.verifySteps([]);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("asks the other device for an offer when the connection fails (bigger id)", async () => {
        // It never sends an offer itself: if both sides fail at the same
        // time, the two devices would send each other an offer.
        setupWebrtc({ id: T2 });
        const { webrtc } = await startDevice();
        const oldPc = await connectFrom(webrtc, T1);
        await expect.waitForSteps(["announce to all", `answer to ${T1}`]);
        // The connection fails: closed at once.
        oldPc.setConnectionState("failed");
        expect(oldPc.closed).toBe(true);
        expect(webrtc.peers.has(T1)).toBe(false);
        // 1 s later: an announce to T1, not an offer.
        await advanceTime(RETRY_DELAYS[0] - MARGIN);
        expect.verifySteps([]);
        await advanceTime(MARGIN);
        await expect.waitForSteps([`announce to ${T1}`]);
        // T1 sends an offer: T2 answers, connected again.
        await receiveSignal(webrtc, {
            type: "offer",
            from: T1,
            to: T2,
            attempt: 2,
            sdp: { type: "offer", sdp: "fake offer" },
        });
        await expect.waitForSteps([`answer to ${T1}`]);
        const { pc } = webrtc.peers.get(T1);
        pc.setConnectionState("connected");
        expect(pc).not.toBe(oldPc);
        expect(webrtc.peerStates().get(T1)).toBe("connected");
        // Nothing else, ever.
        await runAllTimers();
        expect.verifySteps([]);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("reconnects when the data channel closes while the connection is up", async () => {
        // E.g. the channel gave up sending a message the other side never
        // acknowledged: the devices can't talk anymore, even if the
        // connection still looks fine.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const oldPc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        oldPc.channel.closeFromOtherSide();
        expect(oldPc.closed).toBe(true);
        expect(webrtc.peers.has(T2)).toBe(false);
        // 1 s later: a new offer, answered: connected again.
        await advanceTime(RETRY_DELAYS[0]);
        await expect.waitForSteps([`offer to ${T2}`]);
        const pc = await acceptOffer(webrtc, T2);
        expect(pc).not.toBe(oldPc);
        expect(webrtc.peerStates().get(T2)).toBe("connected");
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("waits longer before each reconnection, and gives up after 5 attempts", async () => {
        // E.g. the other device is off: the new connections fail too.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const firstPc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        firstPc.setConnectionState("failed");
        // Attempts 2 to 5: 1, 2, 4, 8 s after the previous failure. Each
        // offer is answered, then the connection fails.
        for (const delay of RETRY_DELAYS) {
            await advanceTime(delay - MARGIN);
            expect.verifySteps([]);
            await advanceTime(MARGIN);
            await expect.waitForSteps([`offer to ${T2}`]);
            const { pc } = webrtc.peers.get(T2);
            await receiveAnswer(webrtc, lastSent("offer"));
            await waitUntil(() => pc.signalingState === "stable");
            pc.setConnectionState("failed");
        }
        // Attempt 5 failed too: T1 gives up.
        await runAllTimers();
        expect.verifySteps([]);
        expect(webrtc.peers.size).toBe(0);
        expect(webrtc.peerStates().has(T2)).toBe(false);
        // T2 announces itself again: T1 tries again.
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await expect.waitForSteps([`offer to ${T2}`]);
    });

    test("waits the shortest delay again once reconnected", async () => {
        // The failures before a successful reconnection don't count anymore.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const firstPc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        // The connection fails, and is rebuilt.
        firstPc.setConnectionState("failed");
        await advanceTime(RETRY_DELAYS[0]);
        await expect.waitForSteps([`offer to ${T2}`]);
        const pc = await acceptOffer(webrtc, T2);
        // The new connection works.
        webrtc.broadcast("Hi");
        expect(pc.channel.messages).toEqual([
            { type: "text", text: `Hello world from ${T1}` },
            { type: "text", text: "Hi" },
        ]);
        // It fails too: 1 s again before the next offer, not 2 s.
        pc.setConnectionState("failed");
        await advanceTime(RETRY_DELAYS[0] - MARGIN);
        expect.verifySteps([]);
        await advanceTime(MARGIN);
        await expect.waitForSteps([`offer to ${T2}`]);
    });

    test("shows the device as reconnecting while waiting for the next attempt", async () => {
        // The debug popup lists the peers with their state: a failed
        // connection that will be rebuilt must not look like a device that
        // left.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        pc.setConnectionState("failed");
        expect(webrtc.peerStates().get(T2)).toBe("reconnecting");
        // The new attempt starts: the state of its connection.
        await advanceTime(RETRY_DELAYS[0]);
        await expect.waitForSteps([`offer to ${T2}`]);
        expect(webrtc.peerStates().get(T2)).toBe("new");
        // Its offer isn't answered: reconnecting again.
        await advanceTime(ANSWER_TIMEOUT);
        expect(webrtc.peerStates().get(T2)).toBe("reconnecting");
    });

    test("doesn't reconnect to a device that leaves", async () => {
        // A device that leaves (tab closed, page reloaded) closes its
        // connections, which looks like a broken channel on the other side:
        // it says goodbye first.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        pc.channel.receive({ type: "bye" });
        pc.channel.closeFromOtherSide();
        expect(pc.closed).toBe(true);
        expect(webrtc.peers.has(T2)).toBe(false);
        expect(webrtc.peerStates().has(T2)).toBe(false);
        // Never an offer.
        await runAllTimers();
        expect.verifySteps([]);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("says goodbye to the other devices when it leaves", async () => {
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        const channel = pc.channel;
        webrtc.stop("pagehide");
        expect(channel.messages.at(-1)).toEqual({ type: "bye" });
        expect(channel.readyState).toBe("closed");
        expect(pc.closed).toBe(true);
        expect(loggedErrors(webrtc)).toEqual([]);
    });
});

describe("heartbeat", () => {
    // A connection can look fine while the other device is gone: its page is
    // frozen (its network still answers the browser's checks), or it crashed
    // or slept and the browser takes a long time to set the connection to
    // "failed", if it ever does. Each device pings the other ones over the
    // data channel, which answer at once: a device that answers nothing for
    // too long is reconnected, like after a failure.

    function hasPeerLog(webrtc, peerId, text) {
        return webrtc.logger
            .logs()
            .some((log) => log.type === "peer" && log.peer === peerId && log.text === text);
    }

    test("pings the other devices every 10 s", async () => {
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        await advanceTime(PING_INTERVAL - MARGIN);
        expect(pc.channel.pings).toBe(0);
        await advanceTime(MARGIN);
        expect(pc.channel.pings).toBe(1);
        await advanceTime(PING_INTERVAL);
        expect(pc.channel.pings).toBe(2);
    });

    test("keeps a connection whose pings are answered, without logging them", async () => {
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        const logCount = webrtc.logger.logs().length;
        // Four times the heartbeat timeout.
        await advanceTime(4 * HEARTBEAT_TIMEOUT);
        expect(pc.channel.pings).toBeGreaterThan(10);
        expect.verifySteps([]);
        expect(webrtc.peers.get(T2).pc).toBe(pc);
        expect(pc.closed).toBe(false);
        expect(webrtc.peerStates().get(T2)).toBe("connected");
        // A ping every 10 s would drown the other logs.
        expect(webrtc.logger.logs().length).toBe(logCount);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("answers the pings of the other devices at once, without logging them", async () => {
        setupWebrtc({ id: T2 });
        const { webrtc } = await startDevice();
        await connectFrom(webrtc, T1);
        await expect.waitForSteps(["announce to all", `answer to ${T1}`]);
        const { channel } = webrtc.peers.get(T1);
        const logCount = webrtc.logger.logs().length;
        channel.receive({ type: "ping" });
        expect(channel.sent.at(-1)).toEqual({ type: "pong" });
        expect(webrtc.logger.logs().length).toBe(logCount);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    for (const id of [T1, T2]) {
        const side = id === T1 ? "smaller id" : "bigger id";
        const peerId = id === T1 ? T2 : T1;
        test(`reconnects to a connected device that stops answering the pings (${side})`, async () => {
            setupWebrtc({ id });
            const { webrtc } = await startDevice();
            const oldPc =
                id === T1 ? await connectTo(webrtc, peerId) : await connectFrom(webrtc, peerId);
            await expect.waitForSteps([
                "announce to all",
                id === T1 ? `offer to ${peerId}` : `answer to ${peerId}`,
            ]);
            const { channel: oldChannel } = webrtc.peers.get(peerId);
            // The first ping is answered, then the other device stops
            // answering, while the connection stays connected.
            await advanceTime(PING_INTERVAL);
            expect(oldChannel.pings).toBe(1);
            oldChannel.answerPings = false;
            // 30 s after the last pong: closed, and shown as reconnecting.
            await advanceTime(HEARTBEAT_TIMEOUT - MARGIN);
            expect(oldPc.closed).toBe(false);
            expect(webrtc.peerStates().get(peerId)).toBe("connected");
            await advanceTime(MARGIN);
            expect(oldPc.closed).toBe(true);
            expect(oldChannel.readyState).toBe("closed");
            expect(webrtc.peers.has(peerId)).toBe(false);
            expect(webrtc.peerStates().get(peerId)).toBe("reconnecting");
            expect(hasPeerLog(webrtc, peerId, "closed: no heartbeat")).toBe(true);
            // 1 s later: the smaller id sends a new offer, the bigger id asks
            // for one. A new connection opens.
            await advanceTime(RETRY_DELAYS[0]);
            let pc;
            if (id === T1) {
                await expect.waitForSteps([`offer to ${T2}`]);
                pc = await acceptOffer(webrtc, T2);
            } else {
                await expect.waitForSteps([`announce to ${T1}`]);
                pc = await connectFrom(webrtc, T1, { attempt: 2 });
                await expect.waitForSteps([`answer to ${T1}`]);
            }
            expect(pc).not.toBe(oldPc);
            // The new connection has its own heartbeat, answered: the one of
            // the old connection doesn't close it.
            const { channel } = webrtc.peers.get(peerId);
            await advanceTime(2 * HEARTBEAT_TIMEOUT);
            expect(channel.pings).toBeGreaterThan(0);
            expect.verifySteps([]);
            expect(webrtc.peers.get(peerId).pc).toBe(pc);
            expect(webrtc.peerStates().get(peerId)).toBe("connected");
            expect(loggedErrors(webrtc)).toEqual([]);
        });
    }

    test("reconnects to a device disconnected for longer than the heartbeat timeout", async () => {
        // Longer than a network hiccup: the browser may wait much longer
        // before setting the connection to "failed", or never do it.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const oldPc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        // Disconnected right after the channel opened: no pong ever.
        oldPc.channel.answerPings = false;
        oldPc.setConnectionState("disconnected");
        // 30 s after the channel opened: closed.
        await advanceTime(HEARTBEAT_TIMEOUT - MARGIN);
        expect(oldPc.closed).toBe(false);
        expect(webrtc.peerStates().get(T2)).toBe("disconnected");
        await advanceTime(MARGIN);
        expect(oldPc.closed).toBe(true);
        expect(webrtc.peerStates().get(T2)).toBe("reconnecting");
        expect(hasPeerLog(webrtc, T2, "closed: no heartbeat")).toBe(true);
        // 1 s later: a new offer, answered: connected again.
        await advanceTime(RETRY_DELAYS[0]);
        await expect.waitForSteps([`offer to ${T2}`]);
        const pc = await acceptOffer(webrtc, T2);
        expect(pc).not.toBe(oldPc);
        expect(webrtc.peerStates().get(T2)).toBe("connected");
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("stops pinging a device that leaves", async () => {
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        await advanceTime(PING_INTERVAL);
        const { channel } = pc;
        channel.receive({ type: "bye" });
        channel.closeFromOtherSide();
        const pings = channel.pings;
        await advanceTime(2 * HEARTBEAT_TIMEOUT);
        expect(channel.pings).toBe(pings);
        expect.verifySteps([]);
        expect(webrtc.peerStates().has(T2)).toBe(false);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("stops pinging when it leaves", async () => {
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        webrtc.stop("pagehide");
        await advanceTime(2 * HEARTBEAT_TIMEOUT);
        expect(pc.channel.pings).toBe(0);
        expect(loggedErrors(webrtc)).toEqual([]);
    });
});

describe("degraded environments", () => {
    /**
     * @returns {number} number of the errors logged starting with `text`
     */
    function countErrors(webrtc, text) {
        return loggedErrors(webrtc).filter((error) => error.startsWith(text)).length;
    }

    /**
     * Starts the device, and makes its first announce fail once the bus is
     * connected: the bus won't connect again by itself, unlike when the
     * server is down. Must be called before the PoS starts.
     *
     * The announce is held until then: the device announces itself after
     * the PoS subscribed to the bus channel, before or after the bus connects.
     * A failure before would be retried by the connection of the bus.
     */
    async function startWithFailedAnnounce(server) {
        let busConnected = false;
        addBusServiceListeners(["BUS:CONNECT", () => (busConnected = true)]);
        const { promise, resolve } = Promise.withResolvers();
        server.held = promise;
        server.reachable = false;
        const { webrtc } = await startDevice();
        await waitUntil(() => busConnected && server.waiting === 1);
        server.held = null;
        resolve();
        await waitUntil(() => countErrors(webrtc, "Failed to announce") > 0);
        expect(countErrors(webrtc, "Failed to announce")).toBe(1);
        return webrtc;
    }

    test("does nothing without WebRTC, and says it once", async () => {
        // E.g. an old browser, or a kiosk browser without WebRTC: the PoS
        // works as usual, without the connections to the other devices.
        setupWebrtc();
        patch(window, { RTCPeerConnection: undefined });
        const { webrtc } = await startDevice();
        // Another device announces itself, and the announce reaches this
        // tab (e.g. the bus is shared with another tab): nothing happens.
        webrtc.bus.addChannel(webrtcChannel(odoo.pos_config_id));
        await waitForChannels([webrtcChannel(odoo.pos_config_id)]);
        webrtc.bus.subscribe(webrtcSignalType(odoo.pos_config_id), () => expect.step("received"));
        sendOnBus({ type: "announce", from: T2 });
        await expect.waitForSteps(["received"]);
        webrtc.broadcast("Hi");
        await runAllTimers();
        // No announce either: the other devices would try to connect to it.
        expect.verifySteps([]);
        expect(webrtc.peers.size).toBe(0);
        expect(webrtc.logger.logs().map(({ type, text }) => `${type}: ${text}`)).toEqual([
            "lifecycle: WebRTC not supported by this browser",
        ]);
    });

    test("announces itself again when its announce fails while the bus is connected", async () => {
        // E.g. the server answered with an error: nobody would know this
        // device, and no reconnection of the bus would announce it again.
        const { server } = setupWebrtc();
        await startWithFailedAnnounce(server);
        server.reachable = true;
        await advanceTime(RETRY_DELAYS[0] - MARGIN);
        expect.verifySteps([]);
        await advanceTime(MARGIN);
        await expect.waitForSteps(["announce to all"]);
        // Announced: nothing else, ever.
        await runAllTimers();
        expect.verifySteps([]);
    });

    test("waits longer before announcing itself again, and gives up after 5 attempts", async () => {
        // The bus announces it again once it reconnects, as when its
        // announce fails while the server is down.
        const { server } = setupWebrtc();
        const webrtc = await startWithFailedAnnounce(server);
        // Announces 2 to 5: 1, 2, 4, 8 s after the previous failure.
        let failures = 1;
        for (const delay of RETRY_DELAYS) {
            await advanceTime(delay - MARGIN);
            expect(countErrors(webrtc, "Failed to announce")).toBe(failures);
            await advanceTime(MARGIN);
            failures++;
            await waitUntil(() => countErrors(webrtc, "Failed to announce") === failures);
        }
        // Then it gives up.
        await runAllTimers();
        expect(countErrors(webrtc, "Failed to announce")).toBe(5);
        // The websocket reconnects: it announces itself again.
        server.reachable = true;
        await dropWebsocket();
        await expect.waitForSteps(["announce to all"]);
    });

    test("gives up sending offers that the server rejects", async () => {
        // E.g. the session expired: each offer fails at once. Don't send them
        // forever.
        const { server } = setupWebrtc();
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        server.error = makeServerError({
            errorName: "odoo.http.SessionExpiredException",
            message: "Session expired",
        });
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await waitUntil(() => countErrors(webrtc, "Failed to send the offer") === 1);
        // Offers 2 to 5: 1, 2, 4, 8 s after the previous failure.
        let failures = 1;
        for (const delay of RETRY_DELAYS) {
            await advanceTime(delay);
            failures++;
            await waitUntil(() => countErrors(webrtc, "Failed to send the offer") === failures);
        }
        // Then it gives up.
        await runAllTimers();
        expect(countErrors(webrtc, "Failed to send the offer")).toBe(5);
        expect(webrtc.peers.size).toBe(0);
        expect(webrtc.peerStates().has(T2)).toBe(false);
    });

    test("gives up asking for an offer when the server rejects it", async () => {
        // Same thing for the bigger id, asking the other device for an offer.
        const { server } = setupWebrtc({ id: T2 });
        const { webrtc } = await startDevice();
        await expect.waitForSteps(["announce to all"]);
        server.error = makeServerError({
            errorName: "odoo.http.SessionExpiredException",
            message: "Session expired",
        });
        await receiveSignal(webrtc, { type: "announce", from: T1 });
        await waitUntil(() => countErrors(webrtc, "Failed to announce") === 1);
        // Announces 2 to 5: 15 s + 1, 2, 4, 8 s after the previous one.
        let failures = 1;
        for (const delay of RETRY_DELAYS) {
            await advanceTime(ANSWER_TIMEOUT + delay);
            failures++;
            await waitUntil(() => countErrors(webrtc, "Failed to announce") === failures);
        }
        // Then it gives up.
        await runAllTimers();
        expect(countErrors(webrtc, "Failed to announce")).toBe(5);
        expect(webrtc.peerStates().has(T1)).toBe(false);
    });

    test("gives up a connection that never gets connected (smaller id)", async () => {
        // E.g. the devices are on networks that can't reach each other: the
        // answer arrives, but the connection stays "connecting".
        setupWebrtc();
        const { webrtc } = await startDevice();
        await receiveSignal(webrtc, { type: "announce", from: T2 });
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        // Attempts 1 to 5: each one answered, then stuck. Attempts 2 to 5
        // start 1, 2, 4, 8 s after the previous one is given up.
        for (const delay of [...RETRY_DELAYS, null]) {
            const { pc } = webrtc.peers.get(T2);
            await receiveAnswer(webrtc, lastSent("offer"));
            await waitUntil(() => pc.signalingState === "stable");
            pc.setConnectionState("connecting");
            await advanceTime(CONNECTION_TIMEOUT - MARGIN);
            expect(pc.closed).toBe(false);
            await advanceTime(MARGIN);
            expect(pc.closed).toBe(true);
            if (delay === null) {
                break;
            }
            expect(webrtc.peerStates().get(T2)).toBe("reconnecting");
            await advanceTime(delay);
            await expect.waitForSteps([`offer to ${T2}`]);
        }
        // Then it gives up.
        await runAllTimers();
        expect.verifySteps([]);
        expect(webrtc.peers.size).toBe(0);
        expect(webrtc.peerStates().has(T2)).toBe(false);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("gives up a connection that never gets connected (bigger id)", async () => {
        // Else the connection would stay: the announces of the other device
        // would be ignored, and they would never connect again.
        setupWebrtc({ id: T2 });
        const { webrtc } = await startDevice();
        await receiveSignal(webrtc, {
            type: "offer",
            from: T1,
            to: T2,
            attempt: 1,
            sdp: { type: "offer", sdp: "fake offer" },
        });
        await expect.waitForSteps(["announce to all", `answer to ${T1}`]);
        const { pc } = webrtc.peers.get(T1);
        pc.setConnectionState("connecting");
        await advanceTime(CONNECTION_TIMEOUT - MARGIN);
        expect(pc.closed).toBe(false);
        await advanceTime(MARGIN);
        expect(pc.closed).toBe(true);
        expect(webrtc.peerStates().get(T1)).toBe("reconnecting");
        // 1 s later: an announce to T1, not an offer.
        await advanceTime(RETRY_DELAYS[0]);
        await expect.waitForSteps([`announce to ${T1}`]);
        expect(loggedErrors(webrtc)).toEqual([]);
    });
});

describe("messages", () => {
    /**
     * @returns {string[]} texts of the message logs, sent and received
     */
    function messageLogs(webrtc) {
        return webrtc.logger
            .logs()
            .filter((log) => log.type === "message")
            .map((log) => log.text);
    }

    test("sends a message only to the devices whose channel is open, and logs the others", async () => {
        // The message isn't kept for later: "Hi" is only a test message, and
        // a message delivered late could be outdated.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc2 = await connectTo(webrtc, T2);
        // T3 announces itself: its connection is in progress.
        await receiveSignal(webrtc, { type: "announce", from: T3 });
        await expect.waitForSteps(["announce to all", `offer to ${T2}`, `offer to ${T3}`]);
        const pc3 = webrtc.peers.get(T3).pc;
        expect(pc3.channel.readyState).toBe("connecting");
        webrtc.broadcast("Hi");
        expect(pc2.channel.messages.at(-1)).toEqual({ type: "text", text: "Hi" });
        expect(pc3.channel.sent).toEqual([]);
        expect(messageLogs(webrtc)).toEqual([
            `sent "Hello world from ${T1}" to ${T2}`,
            `sent "Hi" to ${T2}`,
            `not sent "Hi" to ${T3}: channel connecting`,
        ]);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("keeps sending a message to the other devices when sending it to one fails", async () => {
        // E.g. the send buffer of the channel is full.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc2 = await connectTo(webrtc, T2);
        const pc3 = await connectTo(webrtc, T3);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`, `offer to ${T3}`]);
        patch(pc2.channel, {
            send() {
                // An `Error` rather than the `DOMException` of the browsers:
                // Hoot can't report a `DOMException` that escapes the test (no
                // stack), it aborts the whole run.
                const error = new Error("Failure to send data");
                error.name = "OperationError";
                throw error;
            },
        });
        webrtc.broadcast("Hi");
        expect(pc3.channel.messages.at(-1)).toEqual({ type: "text", text: "Hi" });
        expect(loggedErrors(webrtc)).toEqual(['Failed to send "Hi": Failure to send data']);
        // The connection is kept: the next message may go through.
        expect(webrtc.peers.get(T2).pc).toBe(pc2);
        expect(pc2.closed).toBe(false);
    });

    test("ignores an invalid message, and keeps the connection", async () => {
        // E.g. a device running another version of the PoS.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        pc.channel.receiveRaw("not json");
        pc.channel.receiveRaw("null");
        pc.channel.receive({ type: "text", text: "Hi" });
        expect(messageLogs(webrtc)).toEqual([
            `sent "Hello world from ${T1}" to ${T2}`,
            `ignored invalid message from ${T2}`,
            `ignored invalid message from ${T2}`,
            `received "Hi" from ${T2}`,
        ]);
        expect(webrtc.peers.get(T2).pc).toBe(pc);
        expect(pc.closed).toBe(false);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("ignores a message of an unknown type", async () => {
        // E.g. sent by a newer version of the PoS.
        setupWebrtc();
        const { webrtc } = await startDevice();
        const pc = await connectTo(webrtc, T2);
        await expect.waitForSteps(["announce to all", `offer to ${T2}`]);
        pc.channel.receive({ type: "order", order: {} });
        expect(messageLogs(webrtc)).toEqual([
            `sent "Hello world from ${T1}" to ${T2}`,
            `ignored message of type "order" from ${T2}`,
        ]);
        expect(webrtc.peers.get(T2).pc).toBe(pc);
        expect(loggedErrors(webrtc)).toEqual([]);
    });

    test("ignores the messages of a replaced connection", async () => {
        // A message can still be on its way when its channel closes: once the
        // connection is replaced, it must not affect the new one.
        setupWebrtc({ id: T2 });
        const { webrtc } = await startDevice();
        const oldPc = await connectFrom(webrtc, T1);
        const oldChannel = webrtc.peers.get(T1).channel;
        // T1 rebuilds the connection: a new offer replaces the old one.
        const pc = await connectFrom(webrtc, T1, { attempt: 2 });
        await expect.waitForSteps(["announce to all", `answer to ${T1}`, `answer to ${T1}`]);
        expect(oldPc.closed).toBe(true);
        oldChannel.receive({ type: "text", text: "Old" });
        oldChannel.receive({ type: "bye" });
        expect(webrtc.peers.get(T1)?.pc).toBe(pc);
        expect(pc.closed).toBe(false);
        expect(webrtc.peerStates().get(T1)).toBe("connected");
        expect(messageLogs(webrtc)).not.toInclude(`received "Old" from ${T1}`);
        expect(loggedErrors(webrtc)).toEqual([]);
    });
});

describe("device id", () => {
    // The server only relays the messages of a device whose id ends with
    // the tag of its session: another user can't pretend to be it.
    const TAG = "0123456789abcdef";
    const ID = new RegExp(`^[0-9a-f]{8}-[0-9a-f-]{27}\\.${TAG}$`);

    test("ends with the tag of its session, which the logs leave out", async () => {
        patch(session, { pos_webrtc_tag: TAG });
        setupWebrtc({ id: null });
        const { webrtc } = await startDevice();
        expect(webrtc.id).toMatch(ID);
        expect(lastSent("announce").from).toBe(webrtc.id);
        expect.verifySteps(["announce to all"]);
        expect(webrtc.logger.shortId(webrtc.id)).toBe(webrtc.id.slice(0, 8));
    });

    test("keeps the tag of its session when it takes a new id", async () => {
        // E.g. its page is restored from the back/forward cache.
        patch(session, { pos_webrtc_tag: TAG });
        setupWebrtc({ id: null });
        const { webrtc } = await startDevice();
        const firstId = webrtc.id;
        webrtc.stop("pagehide");
        await webrtc.resume();
        expect(webrtc.id).not.toBe(firstId);
        expect(webrtc.id).toMatch(ID);
        expect(lastSent("announce").from).toBe(webrtc.id);
        expect.verifySteps(["announce to all", "announce to all"]);
    });
});
