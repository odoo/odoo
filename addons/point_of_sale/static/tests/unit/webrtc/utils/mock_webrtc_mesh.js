import { makeWebrtcService } from "./webrtc_service";
import { MockRTCDataChannel, MockRTCPeerConnection } from "./mock_webrtc";

// PeerState extends Set so tests assert directly on the peer's known messages.
// pushState(text) adds to the Set and broadcasts to all connected peers.
// While disconnected, pushState still updates the local Set but sends to nobody
// (sendToAll iterates empty connections). The accumulated state is included in
// the snapshot when the peer rejoins via addPeer({ resume }).
class PeerState extends Set {
    constructor(id, service) {
        super();
        this._id = id;
        this._service = service;
    }

    pushState(text) {
        this.add(text);
        this._service.pushMessage("message", [text]);
        this._service._flush();
    }
}

function setupHandlers(service, state, id) {
    // Live delivery: merge each incoming message into the flat set
    service.register("message", (peer, text) => state.add(text));

    // Snapshot exchange: send full known set on connect; merge on receive.
    // Sending the full set (not just own messages) means any peer can catch
    // up a rejoiner even if the original sender is currently offline.
    service.registerSnapshot("messages", {
        build: () => [...state],
        apply: (peer, payload) => {
            for (const msg of payload) {
                state.add(msg);
            }
        },
    });
}

/**
 * A mesh of real WebRtcService instances wired together via mock channels.
 *
 * addPeer(id, group, { resume }) returns a PeerState (Set<string>).
 * Pass resume: existingState to reconnect with accumulated offline state —
 * the snapshot sent on rejoin will include everything the peer pushed while
 * disconnected, so all other peers converge to the full union immediately.
 *
 * Without resume, the peer starts fresh from an empty Set.
 * The PeerState reference from a previous addPeer remains valid after
 * removePeer — it shows what that peer last knew before going offline.
 */
export class MockWebRtcMesh {
    peers = new Map(); // id → { service, state }

    // Bypasses ICE/SDP — each side's channel.send() calls the other's _onChannelMessage().
    _wire(serviceA, idA, serviceB, idB) {
        const chAB = new MockRTCDataChannel();
        const chBA = new MockRTCDataChannel();
        chAB.send = (data) => serviceB._onChannelMessage(idA, data);
        chBA.send = (data) => serviceA._onChannelMessage(idB, data);
        serviceA._addPeer(idB, {
            pc: new MockRTCPeerConnection(),
            channel: chAB,
            group: serviceB.group,
            deviceUuid: serviceB._deviceUuid,
        });
        serviceB._addPeer(idA, {
            pc: new MockRTCPeerConnection(),
            channel: chBA,
            group: serviceA.group,
            deviceUuid: serviceA._deviceUuid,
        });
        serviceA._onChannelOpen(idB);
        serviceB._onChannelOpen(idA);
    }

    async addPeer(id, group = "terminal", { resume, setup, deviceUuid } = {}) {
        const service = await makeWebrtcService({ id, group, deviceUuid });

        let state;
        if (resume) {
            // Reuse the existing Set (which may contain offline pushState calls),
            // but rebind the service so future pushState broadcasts on the new connection.
            state = resume;
            state._service = service;
        } else {
            state = new PeerState(id, service);
        }

        setupHandlers(service, state, id);
        // Awaited before wiring so all handlers are registered before _onChannelOpen fires
        if (setup) {
            await setup(service);
        }

        // Wire to every peer already in the mesh — triggers snapshot exchange on both sides
        for (const [existingId, { service: existingService }] of this.peers) {
            this._wire(service, id, existingService, existingId);
        }

        this.peers.set(id, { service, state });
        return state;
    }

    // Simulates a peer going away (clean disconnect, zombie cleanup, or browser close).
    // Closes the connection on every other peer's side. The PeerState reference
    // remains valid — pushState calls while offline still update the local Set
    // (but broadcast to nobody since connections are empty).
    removePeer(id) {
        for (const [otherId, { service: other }] of this.peers) {
            if (otherId !== id) {
                other._closeConnection(id);
            }
        }
        this.peers.get(id)?.service.leave();
        this.peers.delete(id);
    }
}
