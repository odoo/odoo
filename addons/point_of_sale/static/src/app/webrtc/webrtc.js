import { getOnNotified } from "@point_of_sale/utils";
import { WebRTCPeer } from "@point_of_sale/app/webrtc/webrtc_peer";
import { webRTCPeerOffer } from "./webrtc_peer_offer";
import { webRTCPeerAnswer, webRTCHandlePeerAnswer } from "./webrtc_peer_answer";
import { webRTCPeerCandidate } from "./webrtc_peer_candidate";
import enhancedConsole from "../utils/enhanced_console";
import { identifierToString } from "./webrtc_utils";
import { debounce } from "@web/core/utils/timing";

/**
 * Handles WebRTC peer-to-peer connections between users in a
 * Point ofSale (POS) system.
 *
 * This module establishes WebRTC connections between multiple clients
 * via a central signaling server, using a structured multi-step
 * initialization process. Each user is uniquely identified by an ID.
 *
 * Simplified sequence of communication:
 * ┌────────────┐            ┌────────┐            ┌────────────┐
 * │  PoS A     │            │ Server │            │  PoS B     │
 * └────┬───────┘            └────────┘            └────────────┘
 *      └──▶──"init" (id=A)───▶──┐
 *                               └───▶───"init" (id=A)───▶──┐
 *                               ┌───◀───"offer" (id=B)──◀──┘
 *      ┌──◀──"offer" (id=B)──◀──┘
 *      └──▶──"answer" (id=A)─▶──┐
 *                               └───▶───"answer" (id=A)─▶──┐
 *                               ┌──◀─"candidate" (id=B)─◀──┘
 *      ┌─◀─"candidate" (id=B)─◀─┘
 *      └─▶─"candidate" (id=A)─▶─┐
 *                               └──▶─"candidate" (id=A)─▶──┐
 * ┌────────────────────────────────────────────────────────────┐
 * │      WebRTC connection established: data channel open      │
 * └────────────────────────────────────────────────────────────┘
 *
 * Detailed Steps:
 * 1. PoS A opens the POS and sends an "init" message to the server
 *    with its ID.
 * 2. The server forwards this "init" message to all other connected
 *    clients (e.g., PoS B).
 * 3. PoS B receives the "init" and:
 *    - Creates a new RTCPeerConnection.
 *    - Creates an SDP offer.
 *    - Sends an "offer" message to the server with its ID and offer.
 * 4. The server relays the "offer" to PoS A.
 * 5. PoS A receives the "offer" and:
 *    - Creates its own RTCPeerConnection.
 *    - Sets the offer as the remote description.
 *    - Creates an SDP answer.
 *    - Sends an "answer" message to the server with its ID and answer.
 * 6. The server forwards the "answer" to PoS B.
 * 7. PoS B sets the answer as the remote description.
 * 8. PoS B starts gathering ICE candidates and sends them to the
 *    server.
 * 9. The server relays ICE candidates from PoS B to PoS A.
 * 10. PoS A starts gathering its own ICE candidates and sends them
 *     to the server.
 * 11. The server relays ICE candidates from PoS A to PoS B.
 * 12. Both PoS A and PoS B receive and add ICE candidates to their
 *     peer connections.
 * 13. Once enough candidates are exchanged and a viable path is found,
 *     the WebRTC peer-to-peer connection is established.
 * 14. A WebRTC data channel is now open between PoS A and PoS B.
 *
 * We need a STUN and TURN server to ensure that webRTC connections can
 * be established even when clients are behind NATs or firewalls.
 * The STUN server helps clients discover their public IP address and
 * port, while the TURN server relays traffic if a direct peer-to-peer
 * connection cannot be established.
 */
export class WebRTCDataChannel {
    static serviceDependencies = ["orm", "bus_service"];

    constructor() {
        this.setup(...arguments).then(() => this);
    }

    async setup(env, { orm, bus_service }) {
        this.env = env;
        this.orm = orm;
        this.bus = bus_service;

        this.ready = new Promise((r) => (this.markReady = r));
        this.peers = new Map();
        this.onMessage = null;
        this.onPeerChange = null;
        this.messagesQueue = [];
        this.debounceSendMessage = debounce(this.sendMessage.bind(this), 1000);

        this.initializeBusListeners();
        this.startHeartbeat();

        this.markReady(this);
    }

    get nextPeerIdentifier() {
        return {
            config_id: odoo.pos_config_id,
            device_a: odoo.login_number,
            device_b: null,
        };
    }

    /**
     * Initializes the WebRTC connection by sending an "init" message
     * to the server. This message will be receved by other peers
     * to establish a WebRTC connection.
     * @returns {Promise<void>}
     */
    async init() {
        try {
            await this.orm.call("pos.config", "webrtc_signal", [
                odoo.pos_config_id,
                odoo.login_number,
                {
                    data: { type: "init" },
                    identifier: this.nextPeerIdentifier,
                },
            ]);
            enhancedConsole("info", "WEBRTC", "Sent init message to signaling server.");
        } catch {
            enhancedConsole("error", "WEBRTC", "Failed to reach signaling server.");
        }
    }

    /**
     * Starts a heartbeat that sends a ping message to all connected peers
     * every second. This helps to keep the connections alive and detect outdated peers.
     *
     * The heartbeat will check the state of each peer's send channel and
     * if the channel is not open or the peer is outdated, it will clean up that peer.
     * @return {void}
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            for (const peer of this.peers.values()) {
                try {
                    if (peer.isOutdated) {
                        this.cleanPeer(peer.id);
                    }
                } catch (error) {
                    enhancedConsole(
                        "error",
                        "WEBRTC",
                        `${peer.id} - Failed to send heartbeat`,
                        error
                    );
                }
            }

            if (this.peers.size === 0) {
                this.init();
            }
        }, 5000);
    }

    /**
     * Exposed method to send a message to all connected peers.
     * This method iterates over all peers and sends the provided data.
     *
     * @param {Object} data - The data to be sent to all peers.
     * @returns {Promise<void>}
     */
    async sendMessage() {
        const messages = [...this.messagesQueue];
        this.messagesQueue = [];

        const data = {};
        const deletion = {};
        for (const message of messages) {
            if (message.model && !data[message.model]) {
                data[message.model] = {};
                deletion[message.model] = [];
            }

            if (["update", "create"].includes(message.event)) {
                data[message.model][message.id] = message.data;
            }

            if (message.event === "delete" && message.id) {
                deletion[message.model].push(message.id);
            }
        }

        let shouldSend = false;
        for (const key of Object.keys(data)) {
            data[key] = Object.values(data[key]);

            if (data[key].length > 0 || deletion[key].length > 0) {
                shouldSend = true;
            }
        }

        if (!shouldSend) {
            return;
        }

        for (const peer of this.peers.values()) {
            peer.sendMessage({ data, deletion });
        }
    }

    /**
     * Creates a new WebRTC peer connection for the given identifier.
     * If a peer with the same identifier already exists, it will be cleaned up first.
     *
     * @param {Object} params - The parameters for creating a new peer.
     * @param {Object} params.identifier - The identifier for the new peer connection.
     * @param {boolean} [params.isInitiator=false] - Whether this peer is the initiator of the connection.
     * @returns {Promise<WebRTCPeer|boolean>} - The newly created peer or false if initialization failed.
     */
    async createNewPeer({ identifier, isInitiator = false }) {
        try {
            const id = identifierToString(identifier);
            if (this.peers.has(id)) {
                this.cleanPeer(id);
            }

            const peer = new WebRTCPeer({
                orm: this.orm,
                identifier: identifier,
                messageCallback: this.onMessage,
            });
            await peer.init({ isInitiator });

            peer.peer.onconnectionstatechange = () => {
                const state = peer.peer.connectionState;
                if (["disconnected", "failed", "closed"].includes(state)) {
                    this.cleanPeer(peer.id);
                }
            };

            return peer;
        } catch {
            enhancedConsole("error", "WEBRTC", `Failed to initialize first peer connection.`);
            return false;
        }
    }

    /**
     * Initializes the bus listeners for WebRTC signaling messages.
     * The Odoo Websocket will be used as a signaling server to exchange
     * WebRTC signaling messages between peers.
     */
    initializeBusListeners() {
        this.onNotified = getOnNotified(this.bus, odoo.access_token);
        this.onNotified("WEBRTC_SIGNAL", (message) => {
            if (odoo.login_number === message.login_number) {
                return;
            }

            this.handlePeerSignal(message);
        });
    }

    /**
     * Initializes the first peer connection based on the incoming "init" message.
     * It will send an offer to the signaling server to establish a WebRTC connection with
     * other peers.
     *
     * @param {Object} message - The message containing the identifier for the new peer.
     * @param {Object} message.data - The data containing the identifier.
     * @param {Object} message.data.data - The data containing the type of message (should be "init").
     * @param {Object} message.data.identifier - The identifier for the new peer connection.
     * @returns {Promise<void>}
     */
    async initializeFirstPeerConnection(message) {
        const loginNbr = odoo.login_number;
        const identifier = message.data.identifier;

        identifier.device_b = loginNbr;
        const newPeer = await this.createNewPeer({ identifier: identifier, isInitiator: true });
        if (newPeer) {
            await webRTCPeerOffer({ peer: newPeer, orm: this.orm });
            this.peers.set(newPeer.id, newPeer);
        }
    }

    /**
     * Handles incoming WebRTC offer messages. The message identifier device_a must
     * match the current device. That's because the init message contains the current device
     * identifier, and the offer is sent to all potential peers.
     *
     * @param {Object} message - The incoming message containing the offer.
     * @param {Object} message.data - The data containing the identifier and offer.
     * @param {Object} message.data.data - WebRTC offer data.
     * @param {Object} message.data.identifier - The identifier for the peer connection.
     * @returns {Promise<void>}
     */
    async handleOffer(message) {
        if (message.data.identifier.device_a !== odoo.login_number) {
            return;
        }

        const peer = await this.createNewPeer({ identifier: message.data.identifier });
        if (!peer) {
            return;
        }

        this.peers.set(peer.id, peer);

        if (peer) {
            enhancedConsole("info", "WEBRTC", `${peer.id} - Offer received`);
            await webRTCPeerAnswer({ orm: this.orm, peer, message });

            if (peer.pendingCandidates && peer.pendingCandidates.length) {
                for (const candidateMsg of peer.pendingCandidates) {
                    await webRTCPeerCandidate({ orm: this.orm, peer, message: candidateMsg });
                }
                peer.pendingCandidates = [];
            }
        } else {
            enhancedConsole("warn", "WEBRTC", `Failed to create peer for offer`);
        }
    }

    /**
     * Handles incoming WebRTC answer messages. The message identifier device_b must
     * match the current device. This is because the answer is sent in response to an offer
     * that was initiated by the current device.
     *
     * @param {Object} message - The incoming message containing the answer.
     * @param {Object} message.data - The data containing the identifier and answer.
     * @param {Object} message.data.data - WebRTC answer data.
     * @param {Object} message.data.identifier - The identifier for the peer connection.
     * @returns {Promise<void>}
     */
    async handleAnswer(message) {
        if (message.data.identifier.device_b !== odoo.login_number) {
            return;
        }

        const id = identifierToString(message.data.identifier);
        const peer = this.peers.get(id);

        if (peer) {
            enhancedConsole("info", "WEBRTC", `${peer.id} - Answer received`);
            await webRTCHandlePeerAnswer({ orm: this.orm, peer, message });

            if (peer.pendingCandidates && peer.pendingCandidates.length) {
                for (const candidateMsg of peer.pendingCandidates) {
                    await webRTCPeerCandidate({ orm: this.orm, peer, message: candidateMsg });
                }

                peer.pendingCandidates = [];
            }
        } else {
            enhancedConsole("warn", "WEBRTC", `Failed to create an answer for ${id}`);
        }
    }

    /**
     * Handles incoming WebRTC candidate messages. If the peer connection is already established,
     * it will add the candidate to the peer connection. If not, it will queue the candidate
     * until the peer connection is established.
     *
     * @param {Object} message - The incoming message containing the candidate.
     * @param {Object} message.data - The data containing the identifier and candidate.
     * @param {Object} message.data.data - WebRTC candidate data.
     * @param {Object} message.data.identifier - The identifier for the peer connection.
     * @returns {Promise<void>}
     */
    async handleCandidate(message) {
        const id = identifierToString(message.data.identifier);
        const peer = this.peers.get(id);

        if (peer && peer.peer.remoteDescription && peer.peer.remoteDescription.type) {
            enhancedConsole("info", "WEBRTC", `${peer.id} - Candidate received`);
            await webRTCPeerCandidate({ orm: this.orm, peer, message });
        } else if (peer) {
            peer.pendingCandidates = peer.pendingCandidates || [];
            peer.pendingCandidates.push(message);
            enhancedConsole("warn", "WEBRTC", `${peer.id} - Candidate queued`);
        } else {
            enhancedConsole("warn", "WEBRTC", `Failed to handle candidate for ${id}`);
        }
    }

    /**
     * Handles incoming WebRTC signaling messages. Depending on the type of message,
     * it will call the appropriate handler for offer, answer, or initialization.
     * @param {Object} message - The incoming message containing the signaling data.
     * @param {Object} message.data - The data containing the identifier and signaling data.
     * @param {Object} message.data.data - The signaling data containing the type (offer, answer, init).
     * @param {Object} message.data.identifier - The identifier for the peer connection.
     * @returns {Promise<void>}
     */
    async handlePeerSignal(message) {
        switch (message.data.data.type) {
            case "offer":
                await this.handleOffer(message);
                break;
            case "answer":
                await this.handleAnswer(message);
                break;
            case "init":
                await this.initializeFirstPeerConnection(message);
                break;
        }

        if (message.data.data.candidate) {
            await this.handleCandidate(message);
        }
    }

    /**
     * Sometimes, a peer connection may become outdated or disconnected.
     * This function cleans up the peer connection by closing it and removing it
     * from the peers map.
     *
     * @param {string} peerId - The identifier of the peer to clean up.
     */
    cleanPeer(peerId) {
        const peer = this.peers.get(peerId);
        if (!peer) {
            return;
        }

        try {
            if (peer.peer) {
                peer.peer.close();
            }
        } catch (error) {
            enhancedConsole(
                "error",
                "WEBRTC",
                `${peer.id} - Failed to close peer connection`,
                error
            );
        }

        enhancedConsole("warn", "WEBRTC", `${peer.id} - Cleaning`);
        this.peers.delete(peerId);
    }
}
