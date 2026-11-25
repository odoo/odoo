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

    test("does not chunk a payload exactly at MAX_CHUNK_SIZE", () => {
        const channel = new MockRTCDataChannel();
        const peer = new WebRtcPeer("peer-1", { channel });
        const prefixLength = JSON.stringify({ data: "" }).length;
        const message = { data: "x".repeat(WebRtcPeer.MAX_CHUNK_SIZE - prefixLength) };
        const json = JSON.stringify(message);
        expect(json).toHaveLength(WebRtcPeer.MAX_CHUNK_SIZE);

        const result = peer.send(message);

        expect(result).toBe(true);
        expect(channel._sent).toEqual([json]);
    });

    test("splits a payload one byte over MAX_CHUNK_SIZE into two chunk envelopes", () => {
        const channel = new MockRTCDataChannel();
        const peer = new WebRtcPeer("peer-1", { channel });
        const prefixLength = JSON.stringify({ data: "" }).length;
        const message = { data: "x".repeat(WebRtcPeer.MAX_CHUNK_SIZE - prefixLength + 1) };
        const json = JSON.stringify(message);

        const result = peer.send(message);

        expect(result).toBe(true);
        expect(channel._sent).toHaveLength(2);
        const chunks = channel._sent.map((raw) => JSON.parse(raw));
        expect(chunks[0]).toEqual({
            type: "chunk",
            cid: chunks[0].cid,
            index: 0,
            total: 2,
            data: json.slice(0, WebRtcPeer.MAX_CHUNK_SIZE),
        });
        expect(chunks[1]).toEqual({
            type: "chunk",
            cid: chunks[0].cid,
            index: 1,
            total: 2,
            data: json.slice(WebRtcPeer.MAX_CHUNK_SIZE),
        });
    });

    test("splits a large payload into ordered chunks that reassemble to the original JSON", () => {
        const channel = new MockRTCDataChannel();
        const peer = new WebRtcPeer("peer-1", { channel });
        const bigMessage = {
            type: "batch",
            messages: "x".repeat(WebRtcPeer.MAX_CHUNK_SIZE * 2 + 10),
        };
        const json = JSON.stringify(bigMessage);

        const result = peer.send(bigMessage);

        expect(result).toBe(true);
        expect(channel._sent).toHaveLength(3);
        const chunks = channel._sent.map((raw) => JSON.parse(raw));
        expect(chunks.map((c) => c.type)).toEqual(["chunk", "chunk", "chunk"]);
        expect(chunks.map((c) => c.total)).toEqual([3, 3, 3]);
        expect(chunks.map((c) => c.index)).toEqual([0, 1, 2]);
        expect(chunks.every((c) => c.cid === chunks[0].cid)).toBe(true);
        expect(chunks.map((c) => c.data).join("")).toBe(json);
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
