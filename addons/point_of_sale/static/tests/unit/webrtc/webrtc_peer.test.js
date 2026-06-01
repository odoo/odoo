import { describe, expect, test } from "@odoo/hoot";
import { WebRtcPeer } from "@point_of_sale/app/webrtc/webrtc_peer";
import { MockRTCDataChannel, MockRTCPeerConnection } from "./utils/mock_webrtc";
import { freezeDate } from "../utils";

describe("constructor", () => {
    test("stores provided values and initialises all defaults", () => {
        freezeDate("2020-01-01");
        const pc = new MockRTCPeerConnection();
        const channel = new MockRTCDataChannel();
        const peer = new WebRtcPeer("peer-1", { pc, channel, group: "terminal" });
        expect(peer.id).toBe("peer-1");
        expect(peer.pc).toBe(pc);
        expect(peer.channel).toBe(channel);
        expect(peer.group).toBe("terminal");
        expect(peer.lastPong).toBe(Date.now());
        expect(peer.wasConnected).toBe(false);
        expect(peer.retryCount).toBe(0);
        expect(peer.pendingCandidates).toEqual([]);
    });

    test("defaults pc, channel and group to null when not provided", () => {
        const peer = new WebRtcPeer("peer-1", {});
        expect(peer.pc).toBe(null);
        expect(peer.channel).toBe(null);
        expect(peer.group).toBe(null);
    });
});

describe("send", () => {
    test("serialises message to JSON and returns true when channel is open", () => {
        const channel = new MockRTCDataChannel();
        const peer = new WebRtcPeer("peer-1", { channel });
        const result = peer.send({ type: "ping" });
        expect(result).toBe(true);
        expect(channel._sent).toEqual([JSON.stringify({ type: "ping" })]);
    });

    test("returns false and does not send when channel readyState is connecting", () => {
        const channel = new MockRTCDataChannel({ readyState: "connecting" });
        const peer = new WebRtcPeer("peer-1", { channel });
        const result = peer.send({ type: "ping" });
        expect(result).toBe(false);
        expect(channel._sent).toHaveLength(0);
    });

    test("returns false and does not send when channel readyState is closed", () => {
        const channel = new MockRTCDataChannel({ readyState: "closed" });
        const peer = new WebRtcPeer("peer-1", { channel });
        const result = peer.send({ type: "ping" });
        expect(result).toBe(false);
        expect(channel._sent).toHaveLength(0);
    });

    test("returns false when channel is null", () => {
        const peer = new WebRtcPeer("peer-1", {});
        const result = peer.send({ type: "ping" });
        expect(result).toBe(false);
    });
});

describe("addIceCandidate", () => {
    test("buffers candidate when pc has no remote description", async () => {
        const pc = new MockRTCPeerConnection();
        const peer = new WebRtcPeer("peer-1", { pc });
        await peer.addIceCandidate({ candidate: "a" });
        expect(peer.pendingCandidates).toHaveLength(1);
        expect(pc._candidates).toHaveLength(0);
    });

    test("forwards candidate to pc when remote description is set", async () => {
        const pc = new MockRTCPeerConnection({ remoteDescription: { type: "offer" } });
        const peer = new WebRtcPeer("peer-1", { pc });
        await peer.addIceCandidate({ candidate: "a" });
        expect(peer.pendingCandidates).toHaveLength(0);
        expect(pc._candidates).toHaveLength(1);
    });

    test("skips forwarding when connection is closed even with remote description", async () => {
        const pc = new MockRTCPeerConnection({
            connectionState: "closed",
            remoteDescription: { type: "offer" },
        });
        const peer = new WebRtcPeer("peer-1", { pc });
        await peer.addIceCandidate({ candidate: "a" });
        expect(pc._candidates).toHaveLength(0);
    });

    test("buffers multiple candidates when no remote description", async () => {
        const pc = new MockRTCPeerConnection();
        const peer = new WebRtcPeer("peer-1", { pc });
        await peer.addIceCandidate({ candidate: "a" });
        await peer.addIceCandidate({ candidate: "b" });
        expect(peer.pendingCandidates).toHaveLength(2);
        expect(pc._candidates).toHaveLength(0);
    });
});

describe("flushPendingCandidates", () => {
    test("forwards all buffered candidates to pc in order", async () => {
        const pc = new MockRTCPeerConnection({ remoteDescription: { type: "offer" } });
        const peer = new WebRtcPeer("peer-1", { pc });
        peer.pendingCandidates = [{ candidate: "a" }, { candidate: "b" }, { candidate: "c" }];
        await peer.flushPendingCandidates();
        expect(peer.pendingCandidates).toHaveLength(0);
        expect(pc._candidates).toHaveLength(3);
    });

    test("is a no-op when the buffer is empty", async () => {
        const pc = new MockRTCPeerConnection({ remoteDescription: { type: "offer" } });
        const peer = new WebRtcPeer("peer-1", { pc });
        await peer.flushPendingCandidates();
        expect(peer.pendingCandidates).toHaveLength(0);
        expect(pc._candidates).toHaveLength(0);
    });

    test("skips candidates when pc is closed by the time flush runs", async () => {
        const pc = new MockRTCPeerConnection({ remoteDescription: { type: "offer" } });
        const peer = new WebRtcPeer("peer-1", { pc });
        peer.pendingCandidates = [{ candidate: "a" }, { candidate: "b" }];
        pc.connectionState = "closed";
        await peer.flushPendingCandidates();
        expect(peer.pendingCandidates).toHaveLength(0);
        expect(pc._candidates).toHaveLength(0);
    });
});

describe("close", () => {
    test("closes both channel and pc when both are open", () => {
        const channel = new MockRTCDataChannel();
        channel.onclose = () => {};
        const pc = new MockRTCPeerConnection();
        pc.onconnectionstatechange = () => {};

        const peer = new WebRtcPeer("peer-1", { pc, channel });
        peer.close();
        expect(channel.onclose).toBe(null);
        expect(channel.readyState).toBe("closed");
        expect(pc.onconnectionstatechange).toBe(null);
        expect(pc.connectionState).toBe("closed");
    });

    test("skips both when channel and pc are already closed", () => {
        const channel = new MockRTCDataChannel({ readyState: "closed" });
        const pc = new MockRTCPeerConnection({ connectionState: "closed" });
        channel.onclose = () => {};
        pc.onconnectionstatechange = () => {};
        let channelCloseCalled = false;
        channel.close = () => {
            channelCloseCalled = true;
        };
        let pcCloseCalled = false;
        pc.close = () => {
            pcCloseCalled = true;
        };
        const peer = new WebRtcPeer("peer-1", { pc, channel });
        peer.close();
        expect(channelCloseCalled).toBe(false);
        expect(channel.onclose).not.toBe(null);
        expect(pcCloseCalled).toBe(false);
        expect(pc.onconnectionstatechange).not.toBe(null);
    });

    test("skips channel and pc operations when both are null", () => {
        const peer = new WebRtcPeer("peer-1", {});
        expect(() => peer.close()).not.toThrow();
    });
});
