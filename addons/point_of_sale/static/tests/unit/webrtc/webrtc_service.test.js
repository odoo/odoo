import { describe, expect, test } from "@odoo/hoot";
import { freezeDate } from "../utils";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { addFakePeer, makeWebrtcService } from "./utils/webrtc_service";
import { MockRTCPeerConnection } from "./utils/mock_webrtc";
import { WebRtcService } from "@point_of_sale/app/webrtc/webrtc_service";
import { PeerDto, WebRtcPeer } from "@point_of_sale/app/webrtc/webrtc_peer";

// ─── Public API ───────────────────────────────────────────────────────────

describe("register", () => {
    test("stores handlers by name and is chainable", async () => {
        const webrtc = await makeWebrtcService();

        const action1 = () => "action-1";
        const action2 = () => "action-2";

        const result = webrtc.register("action-1", action1).register("action-2", action2);
        expect(result).toBe(webrtc);
        expect(webrtc._registry.get("action-1")).toBe(action1);
        expect(webrtc._registry.get("action-2")).toBe(action2);
    });
});

describe("pushMessage", () => {
    test("adds message to the queue with action, args and options", async () => {
        const webrtc = await makeWebrtcService();

        webrtc.pushMessage("my_action", ["arg1"], { group: "terminal" });

        expect(webrtc._queue).toEqual([
            { action: "my_action", args: ["arg1"], options: { group: "terminal" } },
        ]);
    });

    test("defaults args to [] and options to {} when not provided", async () => {
        const webrtc = await makeWebrtcService();

        webrtc.pushMessage("my_action");

        expect(webrtc._queue).toEqual([{ action: "my_action", args: [], options: {} }]);
    });
});

describe("sendToAll", () => {
    test("sends messages to every connected peer", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1", { group: "group-1" });
        const peer2 = addFakePeer(webrtc, "peer-2", { group: "group-2" });
        const peer3 = addFakePeer(webrtc, "peer-3", { group: "group-2" });
        const messages = [{ action: "action-1", args: ["arg1", "arg2"] }];

        webrtc.sendToAll(messages);

        const expected = JSON.stringify({ type: "batch", messages });
        expect(peer1.channel._sent).toEqual([expected]);
        expect(peer2.channel._sent).toEqual([expected]);
        expect(peer3.channel._sent).toEqual([expected]);
    });
});

describe("sendToGroup", () => {
    test("sends messages only to peers in the target group", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1", { group: "group-1" });
        const peer2 = addFakePeer(webrtc, "peer-2", { group: "group-2" });
        const peer3 = addFakePeer(webrtc, "peer-3", { group: "group-2" });
        const messages = [{ action: "action-1", args: ["arg1", "arg2"] }];

        webrtc.sendToGroup("group-2", messages);

        const expected = JSON.stringify({ type: "batch", messages });
        expect(peer1.channel._sent).toEqual([]);
        expect(peer2.channel._sent).toEqual([expected]);
        expect(peer3.channel._sent).toEqual([expected]);
    });
});

describe("sendToPeer", () => {
    test("sends messages only to the target peer", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1", { group: "group-1" });
        const peer2 = addFakePeer(webrtc, "peer-2", { group: "group-2" });
        const peer3 = addFakePeer(webrtc, "peer-3", { group: "group-2" });
        const messages = [{ action: "action-1", args: ["arg1", "arg2"] }];

        webrtc.sendToPeer("peer-2", messages);

        const expected = JSON.stringify({ type: "batch", messages });
        expect(peer1.channel._sent).toEqual([]);
        expect(peer2.channel._sent).toEqual([expected]);
        expect(peer3.channel._sent).toEqual([]);
    });
});

describe("registerSnapshot", () => {
    test("registers snapshots correctly", async () => {
        const webrtc = await makeWebrtcService();

        const build1 = () => "build-1";
        const apply1 = (peer, payload) => "apply-1";
        const build2 = () => "build-2";
        const apply2 = (peer, payload) => "apply-2";
        const result = webrtc
            .registerSnapshot("snapshot-1", { build: build1, apply: apply1 })
            .registerSnapshot("snapshot-2", { build: build2, apply: apply2 });
        expect(result).toBe(webrtc);
        expect(webrtc._snapshotRegistry.get("snapshot-1")).toEqual({
            build: build1,
            apply: apply1,
        });
        expect(webrtc._snapshotRegistry.get("snapshot-2")).toEqual({
            build: build2,
            apply: apply2,
        });
    });
});

describe("sendSnapshot", () => {
    test("sends snapshot to the peer with name and payload", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");

        webrtc.sendSnapshot("peer-1", "snapshot-1", { order: 1 });

        expect(peer.channel._sent).toEqual([
            JSON.stringify({
                type: "snapshot",
                name: "snapshot-1",
                snapshot: { order: 1 },
            }),
        ]);
    });

    test("does nothing when peer does not exist", async () => {
        const webrtc = await makeWebrtcService();

        expect(() => webrtc.sendSnapshot("peer-1", "snapshot-1", { order: 1 })).not.toThrow();
    });
});

describe("reAnnounce", () => {
    test("calls webrtc_announce RPC with configId, id, group and device_uuid", async () => {
        const webrtc = await makeWebrtcService({ deviceUuid: "test-uuid" });
        let capturedArgs;
        patchWithCleanup(webrtc.orm, {
            call: async (model, method, args) => {
                capturedArgs = args;
            },
        });

        await webrtc.reAnnounce();

        expect(capturedArgs).toEqual([webrtc.configId, webrtc.id, webrtc.group, "test-uuid"]);
    });

    test("runs full _announce when called before initialization completed", async () => {
        const webrtc = await makeWebrtcService();
        webrtc._initialized = false;
        const calls = [];
        patchWithCleanup(webrtc, {
            _announce: async () => calls.push("_announce"),
        });

        await webrtc.reAnnounce();

        expect(calls).toEqual(["_announce"]);
    });
});

describe("leave", () => {
    test("stops the heartbeat and closes all connections", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, {
            _stopHeartbeat: () => calls.push("_stopHeartbeat"),
            _closeAllConnections: () => calls.push("_closeAllConnections"),
        });

        webrtc.leave();

        expect(calls).toEqual(["_stopHeartbeat", "_closeAllConnections"]);
    });
});

// ─── Queue & flush ────────────────────────────────────────────────────────

describe("_flush", () => {
    test("does nothing when queue is empty", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");

        webrtc._flush();

        expect(peer.channel._sent).toHaveLength(0);
    });

    test("sends to all peers and clears the queue when no group is specified", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1", { group: "group-1" });
        const peer2 = addFakePeer(webrtc, "peer-2", { group: "group-2" });

        webrtc.pushMessage("action-1", ["arg1"]);
        webrtc._flush();

        const expected = JSON.stringify({
            type: "batch",
            messages: [{ action: "action-1", args: ["arg1"] }],
        });
        expect(peer1.channel._sent).toEqual([expected]);
        expect(peer2.channel._sent).toEqual([expected]);
        expect(webrtc._queue).toHaveLength(0);
    });

    test("routes messages to the target group only", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1", { group: "group-1" });
        const peer2 = addFakePeer(webrtc, "peer-2", { group: "group-2" });

        webrtc.pushMessage("action-1", ["arg1"], { group: "group-2" });
        webrtc._flush();

        const expected = JSON.stringify({
            type: "batch",
            messages: [{ action: "action-1", args: ["arg1"] }],
        });
        expect(peer1.channel._sent).toEqual([]);
        expect(peer2.channel._sent).toEqual([expected]);
    });

    test("batches messages separately per group", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1", { group: "group-1" });
        const peer2 = addFakePeer(webrtc, "peer-2", { group: "group-2" });

        webrtc.pushMessage("action-1", ["arg1"], { group: "group-1" });
        webrtc.pushMessage("action-2", ["arg2"], { group: "group-2" });
        webrtc._flush();

        expect(peer1.channel._sent).toEqual([
            JSON.stringify({ type: "batch", messages: [{ action: "action-1", args: ["arg1"] }] }),
        ]);
        expect(peer2.channel._sent).toEqual([
            JSON.stringify({ type: "batch", messages: [{ action: "action-2", args: ["arg2"] }] }),
        ]);
    });

    test("merges sync messages within the same group batch", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1", { group: "group-1" });

        webrtc.pushMessage("sync", [{ id: 1 }], { group: "group-1" });
        webrtc.pushMessage("sync", [{ id: 2 }], { group: "group-1" });
        webrtc._flush();

        const expected = JSON.stringify({
            type: "batch",
            messages: [{ action: "sync", args: [[{ id: 1 }, { id: 2 }]] }],
        });
        expect(peer.channel._sent).toEqual([expected]);
    });
});

describe("_mergeMessages", () => {
    test("returns non-sync messages unchanged", async () => {
        const webrtc = await makeWebrtcService();

        const result = webrtc._mergeMessages([
            { action: "action-1", args: ["arg1"] },
            { action: "action-2", args: ["arg2"] },
        ]);

        expect(result).toEqual([
            { action: "action-1", args: ["arg1"] },
            { action: "action-2", args: ["arg2"] },
        ]);
    });

    test("merges multiple sync messages into one with combined payload", async () => {
        const webrtc = await makeWebrtcService();

        const result = webrtc._mergeMessages([
            { action: "sync", args: [{ id: 1 }] },
            { action: "sync", args: [{ id: 2 }] },
        ]);

        expect(result).toEqual([{ action: "sync", args: [[{ id: 1 }, { id: 2 }]] }]);
    });

    test("places merged sync first then non-sync in original order", async () => {
        const webrtc = await makeWebrtcService();

        const result = webrtc._mergeMessages([
            { action: "sync", args: [{ id: 1 }] },
            { action: "action-1", args: ["arg1"] },
            { action: "sync", args: [{ id: 2 }] },
        ]);

        expect(result).toEqual([
            { action: "sync", args: [[{ id: 1 }, { id: 2 }]] },
            { action: "action-1", args: ["arg1"] },
        ]);
    });

    test("returns empty array when given empty array", async () => {
        const webrtc = await makeWebrtcService();

        expect(webrtc._mergeMessages([])).toEqual([]);
    });
});

// ─── Init ─────────────────────────────────────────────────────────────────

describe("_init", () => {
    test("calls _announce and returns the service instance", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _announce: async () => calls.push(true) });

        const result = await webrtc._init();

        expect(calls).toHaveLength(1);
        expect(result).toBe(webrtc);
    });

    test("skips _announce and returns the service instance when group is not set", async () => {
        const webrtc = await makeWebrtcService();
        webrtc.group = null;
        webrtc._initialized = false;
        const calls = [];
        patchWithCleanup(webrtc, { _announce: async () => calls.push(true) });

        const result = await webrtc._init();

        expect(calls).toHaveLength(0);
        expect(result).toBe(webrtc);
        expect(webrtc._initialized).toBe(false);
    });
});

describe("_announce", () => {
    test("sets id from RPC result, adds bus channel and starts heartbeat", async () => {
        const webrtc = await makeWebrtcService();
        webrtc.id = "old-id";
        const channelCalls = [];
        const heartbeatCalls = [];
        let capturedArgs;
        patchWithCleanup(webrtc.orm, {
            call: async (model, method, args) => {
                capturedArgs = args;
                return { uuid: "self-id", bus_channel: "pos-ch", peer_group: "terminal" };
            },
        });
        patchWithCleanup(webrtc, { _startHeartbeat: () => heartbeatCalls.push(true) });
        patchWithCleanup(webrtc.bus, {
            addChannel: (ch) => channelCalls.push(ch),
            subscribe: () => {},
        });

        await webrtc._announce();

        expect(capturedArgs).toEqual([webrtc.configId, "old-id", webrtc.group, null]);
        expect(webrtc.id).toBe("self-id");
        expect(channelCalls).toEqual(["pos-ch"]);
        expect(heartbeatCalls).toHaveLength(1);
        expect(webrtc._initialized).toBe(true);
    });

    test("WEBRTC_PEER_ANNOUNCE and should connect", async () => {
        const webrtc = await makeWebrtcService();
        const initCalls = [];
        const subscriptions = {};
        patchWithCleanup(webrtc, {
            _initiateConnection: (peer) => initCalls.push(peer),
            _startHeartbeat: () => {},
            _shouldConnect: () => true,
        });
        patchWithCleanup(webrtc.bus, {
            addChannel: () => {},
            subscribe: (channel, cb) => {
                subscriptions[channel] = cb;
            },
        });

        await webrtc._announce();
        subscriptions["pos-ch-WEBRTC_PEER_ANNOUNCE"]({
            peer_id: "peer-1",
            peer_group: "terminal",
            peer_device_uuid: null,
        });

        expect(initCalls).toEqual([{ id: "peer-1", group: "terminal", deviceUuid: null }]);
    });

    test("WEBRTC_PEER_ANNOUNCE and should not connect", async () => {
        const webrtc = await makeWebrtcService();
        const initCalls = [];
        const subscriptions = {};
        patchWithCleanup(webrtc, {
            _initiateConnection: (peer) => initCalls.push(peer),
            _startHeartbeat: () => {},
            _shouldConnect: () => false,
        });
        patchWithCleanup(webrtc.bus, {
            addChannel: () => {},
            subscribe: (channel, cb) => {
                subscriptions[channel] = cb;
            },
        });

        await webrtc._announce();
        subscriptions["pos-ch-WEBRTC_PEER_ANNOUNCE"]({
            peer_id: "peer-1",
            peer_group: "terminal",
            peer_device_uuid: null,
        });

        expect(initCalls).toEqual([]);
    });

    test("routes WEBRTC_SIGNAL to _handleSignal", async () => {
        const webrtc = await makeWebrtcService();
        const signalCalls = [];
        const subscriptions = {};
        patchWithCleanup(webrtc, {
            _handleSignal: (payload) => signalCalls.push(payload),
            _startHeartbeat: () => {},
        });
        patchWithCleanup(webrtc.bus, {
            addChannel: () => {},
            subscribe: (channel, cb) => {
                subscriptions[channel] = cb;
            },
        });

        await webrtc._announce();
        const payload = { type: "offer", from: "peer-1", to: webrtc.id };
        subscriptions["pos-ch-WEBRTC_SIGNAL"](payload);

        expect(signalCalls).toEqual([payload]);
    });
});

describe("_initiateConnection", () => {
    test("creates peer, sets up channel and connection, and sends offer", async () => {
        const webrtc = await makeWebrtcService();
        patchWithCleanup(globalThis, { RTCPeerConnection: MockRTCPeerConnection });
        const setupChannelCalls = [];
        const setupPcCalls = [];
        const signalCalls = [];
        patchWithCleanup(webrtc, {
            _setupChannel: (channel, peerId) => setupChannelCalls.push(peerId),
            _setupPeerConnection: (pc, peerId) => setupPcCalls.push(peerId),
            _signal: async (peerId, msg) => signalCalls.push([peerId, msg]),
        });

        await webrtc._initiateConnection({ id: "peer-1", group: "terminal" });

        const peer = webrtc.connections.get("peer-1");
        expect(peer.group).toBe("terminal");
        expect(peer.retryCount).toBe(0);
        expect(peer.wasConnected).toBe(false);
        expect(peer.pc.localDescription).toEqual({ type: "offer", sdp: "mock-sdp-offer" });
        expect(setupChannelCalls).toEqual(["peer-1"]);
        expect(setupPcCalls).toEqual(["peer-1"]);
        expect(signalCalls).toEqual([
            [
                "peer-1",
                {
                    type: "offer",
                    sdp: { type: "offer", sdp: "mock-sdp-offer" },
                    group: webrtc.group,
                    deviceUuid: null,
                },
            ],
        ]);
    });

    test("closes existing connection before creating a new one", async () => {
        const webrtc = await makeWebrtcService();
        patchWithCleanup(globalThis, { RTCPeerConnection: MockRTCPeerConnection });
        patchWithCleanup(webrtc, {
            _setupChannel: () => {},
            _setupPeerConnection: () => {},
            _signal: async () => {},
        });
        const oldPeer = addFakePeer(webrtc, "peer-1");

        await webrtc._initiateConnection({ id: "peer-1", group: "terminal" });

        expect(oldPeer.pc.connectionState).toBe("closed");
        expect(webrtc.connections.get("peer-1")).not.toBe(oldPeer);
    });

    test("sets retryCount and wasConnected when retryCount is greater than zero", async () => {
        const webrtc = await makeWebrtcService();
        patchWithCleanup(globalThis, { RTCPeerConnection: MockRTCPeerConnection });
        patchWithCleanup(webrtc, {
            _setupChannel: () => {},
            _setupPeerConnection: () => {},
            _signal: async () => {},
        });

        await webrtc._initiateConnection({ id: "peer-1", group: "terminal" }, 2);

        const peer = webrtc.connections.get("peer-1");
        expect(peer.retryCount).toBe(2);
        expect(peer.wasConnected).toBe(true);
    });

    test("closes connection when signal fails", async () => {
        const webrtc = await makeWebrtcService();
        patchWithCleanup(globalThis, { RTCPeerConnection: MockRTCPeerConnection });
        patchWithCleanup(webrtc, {
            _setupChannel: () => {},
            _setupPeerConnection: () => {},
            _signal: async () => {
                throw new Error("signal failed");
            },
        });

        await webrtc._initiateConnection({ id: "peer-1", group: "terminal" });

        expect(webrtc.connections.has("peer-1")).toBe(false);
    });
});

// ─── Peer connection setup ────────────────────────────────────────────────

describe("_setupPeerConnection", () => {
    test("routes ondatachannel to _onDataChannel with peerId and channel", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, {
            _onDataChannel: (peerId, channel) => calls.push([peerId, channel]),
        });
        const pc = { ondatachannel: null, onicecandidate: null, onconnectionstatechange: null };
        const channel = {};

        webrtc._setupPeerConnection(pc, "peer-1");
        pc.ondatachannel({ channel });

        expect(calls).toEqual([["peer-1", channel]]);
    });

    test("routes onicecandidate to _onIceCandidate with peerId and candidate", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, {
            _onIceCandidate: (peerId, candidate) => calls.push([peerId, candidate]),
        });
        const pc = { ondatachannel: null, onicecandidate: null, onconnectionstatechange: null };
        const candidate = { candidate: "a" };

        webrtc._setupPeerConnection(pc, "peer-1");
        pc.onicecandidate({ candidate });

        expect(calls).toEqual([["peer-1", candidate]]);
    });

    test("routes onconnectionstatechange to _onConnectionStateChange with peerId and connectionState", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, {
            _onConnectionStateChange: (peerId, state) => calls.push([peerId, state]),
        });
        const pc = {
            ondatachannel: null,
            onicecandidate: null,
            onconnectionstatechange: null,
            connectionState: "disconnected",
        };

        webrtc._setupPeerConnection(pc, "peer-1");
        pc.onconnectionstatechange();

        expect(calls).toEqual([["peer-1", "disconnected"]]);
    });
});

describe("_onDataChannel", () => {
    test("sets channel on the peer and calls _setupChannel", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        const calls = [];
        patchWithCleanup(webrtc, {
            _setupChannel: (channel, peerId) => calls.push([channel, peerId]),
        });
        const channel = {};

        webrtc._onDataChannel("peer-1", channel);

        expect(peer.channel).toBe(channel);
        expect(calls).toEqual([[channel, "peer-1"]]);
    });

    test("does nothing when peer does not exist", async () => {
        const webrtc = await makeWebrtcService();

        expect(() => webrtc._onDataChannel("peer-1", {})).not.toThrow();
    });
});

describe("_onIceCandidate", () => {
    test("routes to _signal with ice type and candidate", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _signal: (peerId, msg) => calls.push([peerId, msg]) });

        webrtc._onIceCandidate("peer-1", { candidate: "a" });

        expect(calls).toEqual([["peer-1", { type: "ice", candidate: { candidate: "a" } }]]);
    });

    test("does nothing when candidate is null", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _signal: () => calls.push("called") });

        webrtc._onIceCandidate("peer-1", null);

        expect(calls).toHaveLength(0);
    });
});

describe("_onConnectionStateChange", () => {
    test("calls _closeConnection for disconnected, failed and closed states", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _closeConnection: (peerId) => calls.push(peerId) });

        webrtc._onConnectionStateChange("peer-1", "disconnected");
        webrtc._onConnectionStateChange("peer-1", "failed");
        webrtc._onConnectionStateChange("peer-1", "closed");

        expect(calls).toEqual(["peer-1", "peer-1", "peer-1"]);
    });

    test("does nothing for other states", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _closeConnection: () => calls.push("called") });

        webrtc._onConnectionStateChange("peer-1", "connecting");
        webrtc._onConnectionStateChange("peer-1", "connected");
        webrtc._onConnectionStateChange("peer-1", "new");

        expect(calls).toHaveLength(0);
    });

    test("schedules reconnection after ICE_RECONNECT_DELAY when state is failed and peer was connected", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1", { group: "terminal" });
        peer.wasConnected = true;
        peer.retryCount = 0;
        const calls = [];
        patchWithCleanup(webrtc, {
            _initiateConnection: (p, retry) => calls.push([p, retry]),
        });
        let savedCallback;
        patchWithCleanup(globalThis, {
            setTimeout: (fn, delay) => {
                calls.push(["delay", delay]);
                savedCallback = fn;
            },
        });

        webrtc._onConnectionStateChange("peer-1", "failed");
        savedCallback();

        expect(calls).toEqual([
            ["delay", WebRtcService.ICE_RECONNECT_DELAY],
            [{ id: "peer-1", group: "terminal", deviceUuid: null }, 1],
        ]);
    });

    test("does not schedule reconnection on failed when peer was never connected", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1", { group: "terminal" });
        peer.wasConnected = false;
        const calls = [];
        patchWithCleanup(globalThis, { setTimeout: () => calls.push("setTimeout") });

        webrtc._onConnectionStateChange("peer-1", "failed");

        expect(calls).toHaveLength(0);
    });

    test("does not schedule reconnection for disconnected or closed states", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(globalThis, { setTimeout: () => calls.push("setTimeout") });

        addFakePeer(webrtc, "peer-1", { group: "terminal" }).wasConnected = true;
        webrtc._onConnectionStateChange("peer-1", "disconnected");

        addFakePeer(webrtc, "peer-2", { group: "terminal" }).wasConnected = true;
        webrtc._onConnectionStateChange("peer-2", "closed");

        expect(calls).toHaveLength(0);
    });

    test("skips reconnection when peer has already reconnected before the delay fires", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1", { group: "terminal" });
        peer.wasConnected = true;
        const calls = [];
        patchWithCleanup(webrtc, { _initiateConnection: () => calls.push("called") });
        let savedCallback;
        patchWithCleanup(globalThis, { setTimeout: (fn) => (savedCallback = fn) });

        webrtc._onConnectionStateChange("peer-1", "failed");
        addFakePeer(webrtc, "peer-1", { group: "terminal" }); // peer reconnected before delay fires
        savedCallback();

        expect(calls).toHaveLength(0);
    });
});

// ─── Channel setup ────────────────────────────────────────────────────────

describe("_setupChannel", () => {
    test("routes onopen to _onChannelOpen with peerId", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onChannelOpen: (peerId) => calls.push(peerId) });
        const channel = { onopen: null, onclose: null, onmessage: null };

        webrtc._setupChannel(channel, "peer-1");
        channel.onopen();

        expect(calls).toEqual(["peer-1"]);
    });

    test("routes onclose to _onChannelClose with peerId", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onChannelClose: (peerId) => calls.push(peerId) });
        const channel = { onopen: null, onclose: null, onmessage: null };

        webrtc._setupChannel(channel, "peer-1");
        channel.onclose();

        expect(calls).toEqual(["peer-1"]);
    });

    test("routes onmessage to _onChannelMessage with peerId and data", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, {
            _onChannelMessage: (peerId, data) => calls.push([peerId, data]),
        });
        const channel = { onopen: null, onclose: null, onmessage: null };

        webrtc._setupChannel(channel, "peer-1");
        channel.onmessage({ data: "hello" });

        expect(calls).toEqual([["peer-1", "hello"]]);
    });
});

describe("_onChannelOpen", () => {
    test("sets wasConnected and resets retryCount on the peer", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        peer.retryCount = 3;

        webrtc._onChannelOpen("peer-1");

        expect(peer.wasConnected).toBe(true);
        expect(peer.retryCount).toBe(0);
    });

    test("calls build with the peer dto and sends the snapshot when build returns a value", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1", { group: "terminal", deviceUuid: "uuid-1" });
        const buildCalls = [];
        webrtc.registerSnapshot("snapshot-1", {
            build: (peerDto) => {
                buildCalls.push(peerDto);
                return { order: 1 };
            },
            apply: () => {},
        });

        webrtc._onChannelOpen("peer-1");

        expect(buildCalls).toEqual([new PeerDto("peer-1", "terminal", "uuid-1")]);
        expect(peer.channel._sent).toEqual([
            JSON.stringify({ type: "snapshot", name: "snapshot-1", snapshot: { order: 1 } }),
        ]);
    });

    test("skips sendSnapshot when build returns null", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        webrtc.registerSnapshot("snapshot-1", {
            build: () => null,
            apply: () => {},
        });

        webrtc._onChannelOpen("peer-1");

        expect(peer.channel._sent).toHaveLength(0);
    });

    test("does nothing when peer does not exist", async () => {
        const webrtc = await makeWebrtcService();

        expect(() => webrtc._onChannelOpen("peer-1")).not.toThrow();
    });
});

describe("_onChannelClose", () => {
    test("routes to _closeConnection with peerId", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _closeConnection: (peerId) => calls.push(peerId) });

        webrtc._onChannelClose("peer-1");

        expect(calls).toEqual(["peer-1"]);
    });
});

describe("_onChannelMessage", () => {
    test("routes to _onRemoteMessage with peerId and data", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, {
            _onRemoteMessage: (peerId, data) => calls.push([peerId, data]),
        });

        webrtc._onChannelMessage("peer-1", "hello");

        expect(calls).toEqual([["peer-1", "hello"]]);
    });
});

// ─── Incoming message handling ────────────────────────────────────────────────

describe("_onRemoteMessage", () => {
    test("logs error and returns when message is malformed JSON", async () => {
        const webrtc = await makeWebrtcService();
        const errors = [];
        patchWithCleanup(console, { error: (msg) => errors.push(msg) });

        webrtc._onRemoteMessage("peer-1", "not-json");

        expect(errors).toEqual(["[WebRTC] Malformed message from peer-1"]);
    });

    test("routes batch to _onBatch with from and messages", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onBatch: (from, messages) => calls.push([from, messages]) });
        const messages = [{ action: "action-1", args: ["arg1"] }];

        webrtc._onRemoteMessage("peer-1", JSON.stringify({ type: "batch", messages }));

        expect(calls).toEqual([["peer-1", messages]]);
    });

    test("routes snapshot to _onSnapshot with from and payload", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, {
            _onSnapshot: (from, name, snapshot) => calls.push([from, name, snapshot]),
        });
        const payload = { name: "snapshot-1", snapshot: { order: 1 } };

        webrtc._onRemoteMessage("peer-1", JSON.stringify({ type: "snapshot", ...payload }));

        expect(calls).toEqual([["peer-1", "snapshot-1", { order: 1 }]]);
    });

    test("routes ping to _onPing with from", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onPing: (from) => calls.push(from) });

        webrtc._onRemoteMessage("peer-1", JSON.stringify({ type: "ping" }));

        expect(calls).toEqual(["peer-1"]);
    });

    test("routes pong to _onPong with from", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onPong: (from) => calls.push(from) });

        webrtc._onRemoteMessage("peer-1", JSON.stringify({ type: "pong" }));

        expect(calls).toEqual(["peer-1"]);
    });

    test("logs error for unknown message type", async () => {
        const webrtc = await makeWebrtcService();
        const errors = [];
        patchWithCleanup(console, { error: (msg) => errors.push(msg) });

        webrtc._onRemoteMessage("peer-1", JSON.stringify({ type: "unknown" }));

        expect(errors).toEqual(['[WebRTC] Unknown message type "unknown" from peer-1']);
    });
});

describe("_onBatch", () => {
    test("calls registered handler with peer and args", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        webrtc.register("action-1", (peer, ...args) => calls.push([peer.id, ...args]));

        webrtc._onBatch("peer-1", [{ action: "action-1", args: ["arg1", "arg2"] }]);

        expect(calls).toEqual([["peer-1", "arg1", "arg2"]]);
    });

    test("calls all handlers in order when multiple messages", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        webrtc.register("action-1", (peer, ...args) => calls.push(["action-1", peer.id, ...args]));
        webrtc.register("action-2", (peer, ...args) => calls.push(["action-2", peer.id, ...args]));

        webrtc._onBatch("peer-1", [
            { action: "action-1", args: ["arg1"] },
            { action: "action-2", args: ["arg2"] },
        ]);

        expect(calls).toEqual([
            ["action-1", "peer-1", "arg1"],
            ["action-2", "peer-1", "arg2"],
        ]);
    });

    test("skips unknown actions and continues processing the rest", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        const errors = [];
        patchWithCleanup(console, { error: (msg) => errors.push(msg) });
        webrtc.register("action-1", (peer, ...args) => calls.push([peer.id, ...args]));

        webrtc._onBatch("peer-1", [
            { action: "unknown", args: [] },
            { action: "action-1", args: ["arg1"] },
        ]);

        expect(errors).toEqual(['[WebRTC] Unknown action "unknown" from peer-1']);
        expect(calls).toEqual([["peer-1", "arg1"]]);
    });
});

describe("_onSnapshot", () => {
    test("routes snapshot to registered apply handler by name", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        addFakePeer(webrtc, "peer-1", { group: "terminal" });
        webrtc.registerSnapshot("snapshot-1", {
            build: () => null,
            apply: (peer, payload) => calls.push([peer, payload]),
        });

        webrtc._onRemoteMessage(
            "peer-1",
            JSON.stringify({
                type: "snapshot",
                name: "snapshot-1",
                snapshot: { order: 1 },
            })
        );

        expect(calls).toEqual([[new PeerDto("peer-1", "terminal", null), { order: 1 }]]);
    });

    test("logs error when snapshot type has no registered handler", async () => {
        const webrtc = await makeWebrtcService();
        const errors = [];
        patchWithCleanup(console, { error: (msg) => errors.push(msg) });

        webrtc._onRemoteMessage(
            "peer-1",
            JSON.stringify({
                type: "snapshot",
                name: "unknown-name",
                snapshot: { order: 1 },
            })
        );

        expect(errors).toEqual(['[WebRTC] Unknown snapshot name "unknown-name" from peer-1']);
    });
});

describe("_onPing", () => {
    test("sends pong to the peer", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");

        webrtc._onPing("peer-1");

        expect(peer.channel._sent).toEqual([JSON.stringify({ type: "pong" })]);
    });

    test("does nothing when peer does not exist", async () => {
        const webrtc = await makeWebrtcService();

        expect(() => webrtc._onPing("peer-1")).not.toThrow();
    });
});

describe("_onPong", () => {
    test("updates lastPong on the peer", async () => {
        freezeDate("2020-01-01");
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");

        webrtc._onPong("peer-1");

        expect(peer.lastPong).toBe(Date.now());
    });

    test("does nothing when peer does not exist", async () => {
        const webrtc = await makeWebrtcService();

        expect(() => webrtc._onPong("peer-1")).not.toThrow();
    });
});

// ─── Signaling ────────────────────────────────────────────────────────────

describe("_signal", () => {
    test("calls webrtc_signal RPC with configId and message merged with to and from", async () => {
        const webrtc = await makeWebrtcService();
        let capturedArgs;
        patchWithCleanup(webrtc.orm, {
            call: async (model, method, args) => {
                capturedArgs = args;
            },
        });

        await webrtc._signal("peer-1", { type: "ice", candidate: "a" });

        expect(capturedArgs).toEqual([
            webrtc.configId,
            { type: "ice", candidate: "a", to: "peer-1", from: webrtc.id },
        ]);
    });
});

describe("_handleSignal", () => {
    test("ignores signal sent from self", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onOffer: () => calls.push("offer") });

        await webrtc._handleSignal({ from: webrtc.id, to: webrtc.id, type: "offer" });

        expect(calls).toHaveLength(0);
    });

    test("ignores signal not addressed to self", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onOffer: () => calls.push("offer") });

        await webrtc._handleSignal({ from: "peer-1", to: "other-peer", type: "offer" });

        expect(calls).toHaveLength(0);
    });

    test("routes offer to _onOffer", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onOffer: (payload) => calls.push(payload) });
        const payload = { from: "peer-1", to: webrtc.id, type: "offer" };

        await webrtc._handleSignal(payload);

        expect(calls).toEqual([payload]);
    });

    test("routes answer to _onAnswer", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onAnswer: (payload) => calls.push(payload) });
        const payload = { from: "peer-1", to: webrtc.id, type: "answer" };

        await webrtc._handleSignal(payload);

        expect(calls).toEqual([payload]);
    });

    test("routes ice to _onIce", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, { _onIce: (payload) => calls.push(payload) });
        const payload = { from: "peer-1", to: webrtc.id, type: "ice" };

        await webrtc._handleSignal(payload);

        expect(calls).toEqual([payload]);
    });

    test("logs error for unknown signal type", async () => {
        const webrtc = await makeWebrtcService();
        const errors = [];
        patchWithCleanup(console, { error: (msg) => errors.push(msg) });

        await webrtc._handleSignal({ from: "peer-1", to: webrtc.id, type: "unknown" });

        expect(errors).toEqual(["[WebRTC] Unknown signal type: unknown"]);
    });
});

describe("_onOffer", () => {
    test("closes existing connection, creates peer and sends answer", async () => {
        const webrtc = await makeWebrtcService();
        patchWithCleanup(globalThis, { RTCPeerConnection: MockRTCPeerConnection });
        const setupCalls = [];
        const signalCalls = [];
        const flushCalls = [];
        patchWithCleanup(webrtc, {
            _setupPeerConnection: (pc, peerId) => setupCalls.push(peerId),
            _signal: async (peerId, msg) => signalCalls.push([peerId, msg]),
        });
        patchWithCleanup(WebRtcPeer.prototype, {
            flushPendingCandidates: async () => flushCalls.push(true),
        });
        addFakePeer(webrtc, "peer-1"); // existing connection to be replaced

        await webrtc._onOffer({
            from: "peer-1",
            to: webrtc.id,
            type: "offer",
            group: "terminal",
            sdp: { type: "offer", sdp: "mock-sdp" },
        });

        const peer = webrtc.connections.get("peer-1");
        expect(peer.group).toBe("terminal");
        expect(peer.pc.remoteDescription).toEqual({ type: "offer", sdp: "mock-sdp" });
        expect(peer.pc.localDescription).toEqual({ type: "answer", sdp: "mock-sdp-answer" });
        expect(flushCalls).toHaveLength(1);
        expect(setupCalls).toEqual(["peer-1"]);
        expect(signalCalls).toEqual([
            ["peer-1", { type: "answer", sdp: { type: "answer", sdp: "mock-sdp-answer" } }],
        ]);
    });

    test("closes connection when an error occurs", async () => {
        const webrtc = await makeWebrtcService();
        patchWithCleanup(globalThis, { RTCPeerConnection: MockRTCPeerConnection });
        patchWithCleanup(MockRTCPeerConnection.prototype, {
            setRemoteDescription: async () => {
                throw new Error("sdp error");
            },
        });
        patchWithCleanup(webrtc, { _setupPeerConnection: () => {} });

        await webrtc._onOffer({
            from: "peer-1",
            to: webrtc.id,
            type: "offer",
            group: "terminal",
            sdp: { type: "offer", sdp: "mock-sdp" },
        });

        expect(webrtc.connections.has("peer-1")).toBe(false);
    });
});

describe("_onAnswer", () => {
    test("sets remote description and flushes pending candidates when peer is in have-local-offer state", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        peer.pc.signalingState = "have-local-offer";
        const flushCalls = [];
        patchWithCleanup(WebRtcPeer.prototype, {
            flushPendingCandidates: async () => flushCalls.push(true),
        });
        const sdp = { type: "answer", sdp: "mock-sdp" };

        await webrtc._onAnswer({ from: "peer-1", sdp });

        expect(peer.pc.remoteDescription).toEqual(sdp);
        expect(flushCalls).toHaveLength(1);
    });

    test("does nothing when peer is not in have-local-offer state", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");

        await webrtc._onAnswer({ from: "peer-1", sdp: { type: "answer", sdp: "mock-sdp" } });

        expect(peer.pc.remoteDescription).toBeEmpty();
    });

    test("does nothing when signalingState is have-remote-offer (glare: both sides sent an offer)", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        peer.pc.signalingState = "have-remote-offer";

        await webrtc._onAnswer({ from: "peer-1", sdp: { type: "answer", sdp: "mock-sdp" } });

        expect(peer.pc.remoteDescription).toBeEmpty();
    });

    test("does nothing when signalingState is closed (pc closed before answer arrived)", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        peer.pc.signalingState = "closed";

        await webrtc._onAnswer({ from: "peer-1", sdp: { type: "answer", sdp: "mock-sdp" } });

        expect(peer.pc.remoteDescription).toBeEmpty();
    });

    test("closes connection when an error occurs", async () => {
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        peer.pc.signalingState = "have-local-offer";
        patchWithCleanup(MockRTCPeerConnection.prototype, {
            setRemoteDescription: async () => {
                throw new Error("sdp error");
            },
        });

        await webrtc._onAnswer({ from: "peer-1", sdp: { type: "answer", sdp: "mock-sdp" } });

        expect(webrtc.connections.has("peer-1")).toBe(false);
    });

    test("does nothing when peer does not exist", async () => {
        const webrtc = await makeWebrtcService();

        await expect(webrtc._onAnswer({ from: "peer-1", sdp: {} })).resolves.toBe(undefined);
    });
});

describe("_onIce", () => {
    test("buffers candidate on the peer when no remote description is set", async () => {
        const webrtc = await makeWebrtcService();
        addFakePeer(webrtc, "peer-1");

        await webrtc._onIce({ from: "peer-1", candidate: { candidate: "a" } });

        expect(webrtc.connections.get("peer-1").pendingCandidates).toHaveLength(1);
    });

    test("does nothing when peer does not exist", async () => {
        const webrtc = await makeWebrtcService();

        await expect(
            webrtc._onIce({ from: "peer-1", candidate: { candidate: "a" } })
        ).resolves.toBe(undefined);
    });
});

// ─── Heartbeat ────────────────────────────────────────────────────────────

describe("_startHeartbeat", () => {
    test("sets the heartbeat timer and fires _cleanupZombies and _sendPing on each tick", async () => {
        const webrtc = await makeWebrtcService();
        const calls = [];
        patchWithCleanup(webrtc, {
            _cleanupZombies: () => calls.push("_cleanupZombies"),
            _sendPing: () => calls.push("_sendPing"),
        });
        patchWithCleanup(globalThis, {
            setInterval: (fn) => {
                fn();
                return 100;
            },
        });

        webrtc._startHeartbeat();

        expect(calls).toEqual(["_cleanupZombies", "_sendPing"]);
        expect(webrtc._heartbeatTimer).toBe(100);
    });
});

describe("_stopHeartbeat", () => {
    test("clears the timer and sets _heartbeatTimer to null", async () => {
        const webrtc = await makeWebrtcService();
        webrtc._heartbeatTimer = 100;

        webrtc._stopHeartbeat();

        expect(webrtc._heartbeatTimer).toBe(null);
    });
});

describe("_sendPing", () => {
    test("sends ping to all connected peers", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1");
        const peer2 = addFakePeer(webrtc, "peer-2");

        webrtc._sendPing();

        const expected = JSON.stringify({ type: "ping" });
        expect(peer1.channel._sent).toEqual([expected]);
        expect(peer2.channel._sent).toEqual([expected]);
    });
});

describe("_cleanupZombies", () => {
    test("closes peers whose lastPong is older than the heartbeat interval", async () => {
        freezeDate("2020-01-01");
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        peer.lastPong = Date.now() - 2 * WebRtcService.HEARTBEAT_INTERVAL - 1;

        webrtc._cleanupZombies();

        expect(webrtc.connections.has("peer-1")).toBe(false);
    });

    test("keeps peers whose lastPong is within two heartbeat intervals", async () => {
        freezeDate("2020-01-01");
        const webrtc = await makeWebrtcService();
        addFakePeer(webrtc, "peer-1"); // lastPong defaults to Date.now() — fresh

        webrtc._cleanupZombies();

        expect(webrtc.connections.has("peer-1")).toBe(true);
    });

    test("keeps peer that missed exactly one interval — requires two missed to be a zombie", async () => {
        freezeDate("2020-01-01");
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        peer.lastPong = Date.now() - WebRtcService.HEARTBEAT_INTERVAL - 1;

        webrtc._cleanupZombies();

        expect(webrtc.connections.has("peer-1")).toBe(true);
    });

    test("schedules reconnection for zombie peers that were previously connected", async () => {
        freezeDate("2020-01-01");
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1", { group: "terminal" });
        peer.lastPong = Date.now() - 2 * WebRtcService.HEARTBEAT_INTERVAL - 1;
        peer.wasConnected = true;
        peer.retryCount = 0;
        const calls = [];
        patchWithCleanup(webrtc, {
            _initiateConnection: (peer, retry) => calls.push([peer, retry]),
        });
        patchWithCleanup(globalThis, {
            setTimeout: (fn, delay) => {
                calls.push(["delay", delay]);
                fn();
            },
        });

        webrtc._cleanupZombies();

        expect(calls).toEqual([
            ["delay", 0],
            [{ id: "peer-1", group: "terminal", deviceUuid: null }, 1],
        ]);
    });

    test("uses exponential backoff delay when retryCount is greater than zero", async () => {
        freezeDate("2020-01-01");
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1", { group: "terminal" });
        peer.lastPong = Date.now() - 2 * WebRtcService.HEARTBEAT_INTERVAL - 1;
        peer.wasConnected = true;
        peer.retryCount = 1;
        const calls = [];
        patchWithCleanup(webrtc, {
            _initiateConnection: (peer, retry) => calls.push([peer, retry]),
        });
        patchWithCleanup(globalThis, {
            setTimeout: (fn, delay) => {
                calls.push(["delay", delay]);
                fn();
            },
        });

        webrtc._cleanupZombies();

        expect(calls).toEqual([
            ["delay", 5_000],
            [{ id: "peer-1", group: "terminal", deviceUuid: null }, 2],
        ]);
    });

    test("does not schedule reconnection for zombie peers that were never connected", async () => {
        freezeDate("2020-01-01");
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1");
        peer.lastPong = Date.now() - 2 * WebRtcService.HEARTBEAT_INTERVAL - 1;
        peer.wasConnected = false;
        const calls = [];
        patchWithCleanup(webrtc, { _initiateConnection: () => calls.push("called") });

        webrtc._cleanupZombies();

        expect(calls).toHaveLength(0);
    });

    test("skips reconnection when peer reconnected before the retry timeout fires", async () => {
        freezeDate("2020-01-01");
        const webrtc = await makeWebrtcService();
        const peer = addFakePeer(webrtc, "peer-1", { group: "terminal" });
        peer.lastPong = Date.now() - 2 * WebRtcService.HEARTBEAT_INTERVAL - 1;
        peer.wasConnected = true;
        peer.retryCount = 0;
        const calls = [];
        patchWithCleanup(webrtc, { _initiateConnection: () => calls.push("called") });
        let savedCallback;
        patchWithCleanup(globalThis, {
            setTimeout: (fn) => {
                savedCallback = fn;
            },
        });

        webrtc._cleanupZombies();
        // peer-1 removed from connections; retry scheduled but not fired yet
        addFakePeer(webrtc, "peer-1", { group: "terminal" }); // peer reconnected in the meantime
        savedCallback();

        expect(calls).toHaveLength(0);
    });
});

// ─── Connection ──────────────────────────────────────────────────────────

describe("_shouldConnect", () => {
    test("returns false for own id", async () => {
        const webrtc = await makeWebrtcService();

        expect(webrtc._shouldConnect({ id: webrtc.id, group: "terminal", deviceUuid: null })).toBe(
            false
        );
    });

    test("terminal to terminal is always allowed", async () => {
        const webrtc = await makeWebrtcService();

        expect(webrtc._shouldConnect({ id: "peer-1", group: "terminal", deviceUuid: null })).toBe(
            true
        );
    });

    test("customer_display to customer_display is always blocked", async () => {
        const webrtc = await makeWebrtcService({ group: "customer_display" });

        expect(
            webrtc._shouldConnect({
                id: "peer-1",
                group: "customer_display",
                deviceUuid: "any-uuid",
            })
        ).toBe(false);
    });

    test("terminal to customer_display requires matching device_uuid", async () => {
        const webrtc = await makeWebrtcService({ deviceUuid: "display-x" });

        expect(
            webrtc._shouldConnect({
                id: "peer-1",
                group: "customer_display",
                deviceUuid: "display-x",
            })
        ).toBe(true);
        expect(
            webrtc._shouldConnect({
                id: "peer-1",
                group: "customer_display",
                deviceUuid: "display-y",
            })
        ).toBe(false);
        expect(
            webrtc._shouldConnect({ id: "peer-1", group: "customer_display", deviceUuid: null })
        ).toBe(false);
    });

    test("customer_display to terminal requires matching device_uuid", async () => {
        const webrtc = await makeWebrtcService({
            group: "customer_display",
            deviceUuid: "display-x",
        });

        expect(
            webrtc._shouldConnect({ id: "peer-1", group: "terminal", deviceUuid: "display-x" })
        ).toBe(true);
        expect(
            webrtc._shouldConnect({ id: "peer-1", group: "terminal", deviceUuid: "display-y" })
        ).toBe(false);
    });

    test("returns false for null or unknown peer group", async () => {
        const webrtc = await makeWebrtcService();

        expect(webrtc._shouldConnect({ id: "peer-1", group: null, deviceUuid: null })).toBe(false);
        expect(webrtc._shouldConnect({ id: "peer-1", group: "kiosk", deviceUuid: null })).toBe(
            false
        );
    });
});

describe("_addPeer", () => {
    test("creates a peer, stores it in connections and returns it", async () => {
        const webrtc = await makeWebrtcService();

        const peer = webrtc._addPeer("peer-1", { group: "terminal" });

        expect(webrtc.connections.get("peer-1")).toBe(peer);
        expect(peer.id).toBe("peer-1");
        expect(peer.group).toBe("terminal");
    });
});

describe("_closeAllConnections", () => {
    test("closes all peers and clears the connections map", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1");
        const peer2 = addFakePeer(webrtc, "peer-2");

        webrtc._closeAllConnections();

        expect(peer1.channel.readyState).toBe("closed");
        expect(peer2.channel.readyState).toBe("closed");
        expect(webrtc.connections.size).toBe(0);
    });
});

describe("_closeConnection", () => {
    test("closes and removes the target peer without affecting others", async () => {
        const webrtc = await makeWebrtcService();
        const peer1 = addFakePeer(webrtc, "peer-1");
        addFakePeer(webrtc, "peer-2");

        webrtc._closeConnection("peer-1");

        expect(peer1.channel.readyState).toBe("closed");
        expect(webrtc.connections.has("peer-1")).toBe(false);
        expect(webrtc.connections.has("peer-2")).toBe(true);
    });

    test("does nothing when peer does not exist", async () => {
        const webrtc = await makeWebrtcService();

        expect(() => webrtc._closeConnection("peer-1")).not.toThrow();
    });
});
