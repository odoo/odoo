import enhancedConsole from "../utils/enhanced_console";
import { identifierToString } from "./webrtc_utils";

const { DateTime } = luxon;

const OUTDATED_PEER_STATE = ["disconnected", "failed", "closed"];
const OUTDATED_PEER_TIMEOUT = 5000;
const PEER_CONFIGURATION = {
    iceServers: [
        { urls: "stun:stun.l.google.com:19302" },
        { urls: "stun:stun2.l.google.com:19302" },
        { urls: "stun:stun3.l.google.com:19302" },
        {
            urls: ["turn:david-monnom.be:3478"],
            username: "moda",
            credential: "D5B3dzef53xrv64bnju3",
        },
    ],
};

/**
 * WebRTCPeer class manages a WebRTC peer connection.
 * It handles the creation of the peer, sending and receiving messages,
 * and managing ICE candidates.
 */
export class WebRTCPeer {
    constructor(...args) {
        this.setup(...args);
    }

    setup({ identifier, orm, messageCallback }) {
        this.identifier = identifier;
        this.orm = orm;
        this.messageCallback = messageCallback;
        this.pendingCandidates = [];
        this.createUnix = DateTime.now().toMillis();
        this.peer = null;
        this.sendChannel = null;
    }

    get id() {
        return identifierToString(this.identifier);
    }

    /**
     * Check if the peer is outdated based on its connection state or creation time.
     * A peer is considered outdated if it is in a disconnected, failed, or closed state,
     * or if it has been created for more than OUTDATED_PEER_TIMEOUT milliseconds without
     * being connected.
     * @returns {boolean} True if the peer is outdated, false otherwise.
     */
    get isOutdated() {
        return (
            (this.peer && OUTDATED_PEER_STATE.includes(this.peer.connectionState)) ||
            (DateTime.now().toMillis() - this.createUnix > OUTDATED_PEER_TIMEOUT &&
                this.peer.connectionState !== "connected")
        );
    }

    /**
     * Initialize the WebRTCPeer instance.
     * This method sets up the peer connection, creates a data channel if the peer is the initiator,
     * and handles incoming data channels if the peer is not the initiator.
     * @param {Object} options - Options for initializing the peer.
     * @param {boolean} options.isInitiator - Whether this peer is the initiator of the connection.
     * @returns {Promise<void>} A promise that resolves when the peer is initialized.
     */
    async init({ isInitiator = false } = {}) {
        try {
            this.peer = new RTCPeerConnection(PEER_CONFIGURATION);
            this.peer.onicecandidate = this.onIceCandidateCallback.bind(this);

            if (isInitiator) {
                this.sendChannel = this.peer.createDataChannel("sendChannel");
                this.setupChannelEvents(this.sendChannel);

                try {
                    this.localOffer = await this.peer.createOffer();
                    await this.peer.setLocalDescription(this.localOffer);
                } catch (error) {
                    enhancedConsole(
                        "error",
                        "WEBRTC",
                        `${this.id} - Failed to create offer: ${error.message}`
                    );
                }
            } else {
                this.peer.ondatachannel = (event) => {
                    this.sendChannel = event.channel;
                    this.setupChannelEvents(this.sendChannel);
                };
            }

            enhancedConsole("success", "WEBRTC", `${this.id} - Local peer created`);
        } catch {
            enhancedConsole("error", "WEBRTC", `${this.id} - Error creating local peer`);
        }
    }

    setupChannelEvents(channel) {
        channel.onmessage = this.peerChannelOnMessageCallback.bind(this);
        channel.onopen = this.peerChannelOnOpenCallback.bind(this);
        channel.onclose = this.peerChannelOnCloseCallback.bind(this);
    }

    sendMessage(data) {
        if (this.sendChannel && this.sendChannel.readyState === "open") {
            this.sendChannel.send(JSON.stringify(data));
        } else {
            enhancedConsole("warn", "WEBRTC", `${this.id} - Tried to send but channel not open`);
        }
    }

    close() {
        try {
            if (this.sendChannel) {
                this.sendChannel.close();
            }
            if (this.peer) {
                this.peer.close();
            }

            enhancedConsole("info", "WEBRTC", `${this.id} - Peer closed`);
        } catch {
            enhancedConsole("error", "WEBRTC", `${this.id} - Error closing peer`);
        }
    }

    async onIceCandidateCallback(event) {
        if (!event.candidate) {
            enhancedConsole("warn", "WEBRTC", `${this.id} - Ice candidate empty`);
            return;
        }

        try {
            await this.orm.call("pos.config", "webrtc_signal", [
                odoo.pos_config_id,
                odoo.login_number,
                {
                    data: event.candidate,
                    identifier: this.identifier,
                },
            ]);
        } catch {
            enhancedConsole("error", "WEBRTC", `${this.id} - Error sending ICE candidate`);
        }
    }

    peerChannelOnMessageCallback(event) {
        try {
            this.messageCallback && this.messageCallback(JSON.parse(event.data));
        } catch {
            enhancedConsole("error", "WEBRTC", `${this.id} - Decoding message failed`);
        }
    }

    peerChannelOnOpenCallback() {
        enhancedConsole("success", "WEBRTC", `${this.id} - Data channel opened`);
    }

    peerChannelOnCloseCallback() {
        enhancedConsole("warn", "WEBRTC", `${this.id} - Data channel closed`);
    }

    addCandidateErrorCallback(error) {
        enhancedConsole("error", "WEBRTC", `${this.id} - Error adding ICE candidate`);
    }
}
