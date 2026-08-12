import { expect, test } from "@odoo/hoot";
import { MockWebRtcMesh } from "./utils/mock_webrtc_mesh";

// ─── Flow tests ───────────────────────────────────────────────────────────────
//
// These tests exercise the full connection lifecycle using real WebRtcService
// instances wired together via mock data channels (see MockWebRtcMesh).
//
// Each peer is a PeerState (Set<string>) with a pushState() method.
// All peers converge to the same flat set of known messages — proving actual
// data convergence rather than just that callbacks fired.
//
// What is proven here that unit tests cannot cover:
//   - pushMessage → _flush → sendToAll → wire → _onBatch → handler fires end-to-end
//   - registerSnapshot.build → sendSnapshot → wire → registerSnapshot.apply across real services
//   - State convergence after disconnect/reconnect cycles, including catch-up via a third peer
//
// Once these pass, real actions (sync, update_customer_display) do not need
// to re-test these connection scenarios — only their own payload logic.

// Sets have insertion-order-sensitive equality in Hoot. expectState() and
// msgs() both sort before comparing so assertions are order-agnostic.
const msgs = (...values) => values.slice().sort();
const peers = (...states) => ({
    toEqual: (expected) => states.forEach((s) => expect([...s].sort()).toEqual(expected)),
});

test("message delivery: any peer sends, all peers converge", async () => {
    const mesh = new MockWebRtcMesh();
    const A = await mesh.addPeer("A");
    const B = await mesh.addPeer("B");
    const C = await mesh.addPeer("C");

    // Single sender — others receive
    A.pushState("a1");
    peers(A, B, C).toEqual(msgs("a1"));

    // Different sender
    B.pushState("b1");
    peers(A, B, C).toEqual(msgs("a1", "b1"));

    // Two peers send — all three converge to the full union
    A.pushState("a2");
    B.pushState("b2");
    peers(A, B, C).toEqual(msgs("a1", "b1", "a2", "b2"));
});

test("disconnect and reconnect: peer catches up via snapshot, double cycle stays clean", async () => {
    const mesh = new MockWebRtcMesh();
    const A = await mesh.addPeer("A");
    const B = await mesh.addPeer("B");
    const C = await mesh.addPeer("C");

    A.pushState("a1");
    A.pushState("a2");

    // B disconnects — its PeerState reference still reflects its last known state
    mesh.removePeer("B");

    A.pushState("a3"); // B misses this
    peers(A, C).toEqual(msgs("a1", "a2", "a3"));
    peers(B).toEqual(msgs("a1", "a2")); // last known before going offline

    // First reconnect: snapshot from A (and C) delivers the missed message
    const B2 = await mesh.addPeer("B");
    peers(A, B2, C).toEqual(msgs("a1", "a2", "a3"));

    A.pushState("a4"); // live delivery
    peers(A, B2, C).toEqual(msgs("a1", "a2", "a3", "a4"));

    // Second disconnect/reconnect cycle
    mesh.removePeer("B");
    A.pushState("a5");
    peers(A, C).toEqual(msgs("a1", "a2", "a3", "a4", "a5"));
    peers(B2).toEqual(msgs("a1", "a2", "a3", "a4")); // last known before going offline

    const B3 = await mesh.addPeer("B");
    peers(A, B3, C).toEqual(msgs("a1", "a2", "a3", "a4", "a5"));

    A.pushState("a6");
    peers(A, B3, C).toEqual(msgs("a1", "a2", "a3", "a4", "a5", "a6"));
});

test("snapshot on join: new peer gets current state; snapshot on reconnect: catches up via any peer", async () => {
    const mesh = new MockWebRtcMesh();
    const A = await mesh.addPeer("A");
    const C = await mesh.addPeer("C");

    A.pushState("a1");
    A.pushState("a2");

    // B joins after A has already sent — snapshot delivers current state immediately
    const B = await mesh.addPeer("B");
    peers(A, B, C).toEqual(msgs("a1", "a2"));

    A.pushState("a3"); // all three connected, live delivery
    peers(A, B, C).toEqual(msgs("a1", "a2", "a3"));

    // B goes offline — A and C receive more messages
    mesh.removePeer("B");
    A.pushState("a4");
    A.pushState("a5");
    peers(A, C).toEqual(msgs("a1", "a2", "a3", "a4", "a5"));
    peers(B).toEqual(msgs("a1", "a2", "a3")); // last known before going offline

    // A also goes offline — only C remains
    mesh.removePeer("A");

    // B rejoins — only C is available, but C holds the full state
    const BNew = await mesh.addPeer("B");
    peers(BNew, C).toEqual(msgs("a1", "a2", "a3", "a4", "a5"));

    // A rejoins — gets the full state from C or BNew
    const ANew = await mesh.addPeer("A");
    peers(ANew, BNew, C).toEqual(msgs("a1", "a2", "a3", "a4", "a5"));
});

test("offline state accumulation: pushState while disconnected merges on reconnect", async () => {
    const mesh = new MockWebRtcMesh();
    const A = await mesh.addPeer("A");
    const B = await mesh.addPeer("B");
    const C = await mesh.addPeer("C");

    A.pushState("a1");
    peers(A, B, C).toEqual(msgs("a1"));

    // B goes offline
    mesh.removePeer("B");

    // B pushes state while offline — connections are empty so _flush sends to nobody.
    // B's local Set still accumulates the values.
    B.pushState("b1");
    B.pushState("b2");
    peers(B).toEqual(msgs("a1", "b1", "b2")); // only in B's local state
    peers(A, C).toEqual(msgs("a1")); // A and C unaware of b1/b2

    // A also updates while B is offline — C receives, B does not
    A.pushState("a2");
    peers(A, C).toEqual(msgs("a1", "a2"));

    // B rejoins carrying its accumulated offline state.
    // resume: B reuses the existing Set so the snapshot build() sends ["a1", "b1", "b2"]
    // to A and C; their snapshots send ["a1", "a2"] back to B.
    const B1 = await mesh.addPeer("B", "terminal", { resume: B });
    peers(A, B1, C).toEqual(msgs("a1", "a2", "b1", "b2"));

    // Live delivery resumes normally for all three
    A.pushState("a3");
    peers(A, B1, C).toEqual(msgs("a1", "a2", "a3", "b1", "b2"));
});

test("double offline: B misses A's update, A goes offline, B recovers full state via C", async () => {
    const mesh = new MockWebRtcMesh();
    const A = await mesh.addPeer("A");
    await mesh.addPeer("B");
    const C = await mesh.addPeer("C");

    // B goes offline first
    mesh.removePeer("B");

    // A updates — only C receives
    A.pushState("a1");
    A.pushState("a2");
    peers(A, C).toEqual(msgs("a1", "a2"));

    // A also goes offline — only C remains with the full state
    mesh.removePeer("A");

    // B rejoins — C is the only peer, but it holds the full state
    const BNew = await mesh.addPeer("B");
    peers(BNew, C).toEqual(msgs("a1", "a2"));
});
