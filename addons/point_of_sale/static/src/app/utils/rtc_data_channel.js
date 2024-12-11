const DEFAULT_ICE_SERVERS = [
    { urls: ["stun:stun1.l.google.com:19302", "stun:stun2.l.google.com:19302"] },
];

const DEBUG_COLOR_MESSAGE = {
    receive_signal: { message: "Receive signal", color: "#6fff6d" },
    send_signal: { message: "Send signal", color: "#6fff6d" },
    send_message: { message: "Send message", color: "#ffd16d" },
    receive_message: { message: "Receive message", color: "#ffd16d" },
    handle_new_peer: { message: "Handle new peer", color: "#b590ff" },
    handle_offer: { message: "Handle offer", color: "#b590ff" },
    handle_answer: { message: "Handle answer", color: "#b590ff" },
    handle_candidate: { message: "Handle candidate", color: "#b590ff" },
};

/**
 * WebRTCManager class is designed to manage WebRTC connections, facilitating peer-to-peer communication.
 * It handles signaling, peer management, and data channel operations.
 */
export class WebRTCManager {
    /**
     * Constructor initializes the manager with data, a signaling function, and a callback.
     * It sets up internal structures for peers, channels, queued ICE candidates, and login numbers.
     * It also sets up a signal listener for RTC signals and announces new peers.
     *
     * @param {Object} options - The options for initializing the WebRTCManager.
     * @param {Object} options.data - The data service from the POS.
     * @param {Function} options.signal - The signaling function for handling RTC signals. (bus_service)
     * @param {Function} options.callback - The callback function to be called on data channel message.
     */
    constructor({ data, signal, callback }) {
        this.data = data;
        this.peers = {};
        this.channels = {};
        this.queuedCandidates = [];
        this.loginNumbers = new Set();
        this.callback = callback;

        signal("RTC_SIGNAL", async (signal) => {
            if (signal.login_number === odoo.login_number) {
                return;
            }

            const data = signal.rtc_params;
            this.debugLog("receive_signal", data);
            this.handleSignal(data, data.peerId);
        });

        this.announceNewPeer();
    }

    get randomString() {
        return Math.random().toString(36).substring(2);
    }

    sendMessage(data = {}) {
        this.debugLog("send_message", data);

        for (const channel of Object.values(this.channels)) {
            if (channel.readyState === "open") {
                channel.send(
                    JSON.stringify({
                        config_id: odoo.pos_config_id,
                        data: data,
                    })
                );
            }
        }
    }

    receiveMessage(json) {
        const data = JSON.parse(json);
        if (data.config_id === odoo.pos_config_id) {
            this.debugLog("receive_message", data.data);
            this.callback(data.data);
        }
    }

    createPeer(peerId) {
        const peer = new RTCPeerConnection({
            iceServers: DEFAULT_ICE_SERVERS,
            peerIdentity: odoo.access_token,
        });

        peer.onicecandidate = (event) => {
            if (event.candidate) {
                this.dispatchSignal({
                    type: "ice-candidate",
                    candidate: event.candidate,
                    peerId: peerId,
                });
            }
        };

        peer.ondatachannel = (event) => {
            const channel = event.channel;
            this.setChannelListeners(channel, peerId);
        };

        peer.onconnectionstatechange = () => {
            if (peer.connectionState === "disconnected" || peer.connectionState === "closed") {
                delete this.peers[peerId];
            }
        };

        return peer;
    }

    createDataChannel(peer, peerId) {
        const channel = peer.createDataChannel("dataChannel");
        this.setChannelListeners(channel, peerId);
    }

    setChannelListeners(channel, peerId) {
        this.channels[peerId] = channel;
        channel.onmessage = (event) => {
            this.receiveMessage(event.data);
        };
    }

    async announceNewPeer() {
        await this.dispatchSignal({
            type: "new-peer",
            login_number: odoo.login_number,
        });
    }

    async handleSignal(data) {
        if (data.type === "new-peer" && !this.loginNumbers.has(data.login_number)) {
            this.handleNewPeer(this.randomString);
        } else if (data.type === "offer" && !this.loginNumbers.has(data.login_number)) {
            this.handleOffer(data, data.peerId);
        } else if (data.type === "answer") {
            this.handleAnswer(data, data.peerId);
        } else if (data.type === "ice-candidate") {
            this.handleIceCandidate(data, data.peerId);
        }

        if (data.login_number) {
            this.loginNumbers.add(data.login_number);
        }
    }

    async handleNewPeer(peerId) {
        if (peerId in this.peers) {
            return;
        }

        const peer = this.createPeer(peerId);
        this.createDataChannel(peer, peerId);
        this.peers[peerId] = peer;

        try {
            const offer = await peer.createOffer();
            await peer.setLocalDescription(offer);
            this.debugLog("handle_new_peer", offer);
        } catch (error) {
            console.log("Error creating offer", error);
        }

        this.dispatchSignal({
            type: "offer",
            offer: peer.localDescription,
            peerId: peerId,
            login_number: odoo.login_number,
        });
    }

    async handleOffer(data, peerId) {
        if (peerId in this.peers) {
            return;
        }

        const peer = this.createPeer(peerId);
        this.peers[peerId] = peer;

        try {
            await peer.setRemoteDescription(new RTCSessionDescription(data.offer));
            const answer = await peer.createAnswer();
            await peer.setLocalDescription(answer);
        } catch (error) {
            console.log("Error creating answer", error);
        }

        this.dispatchSignal({
            type: "answer",
            answer: peer.localDescription,
            peerId: peerId,
        });

        if (peer.queuedIceCandidates) {
            for (const candidate of peer.queuedIceCandidates) {
                try {
                    await peer.addIceCandidate(new RTCIceCandidate(candidate));
                    this.debugLog("handle_offer", candidate);
                } catch (e) {
                    console.error("Error adding queued ice candidate", e);
                }
            }
            peer.queuedIceCandidates = [];
        }
    }

    async handleAnswer(data, peerId) {
        const peer = this.peers[peerId];

        if (!peer) {
            return;
        }

        if (peer) {
            try {
                await peer.setRemoteDescription(new RTCSessionDescription(data.answer));
                this.debugLog("handle_answer", data);
            } catch (error) {
                console.log("Error setting remote description", error);
            }
        }
    }

    async handleIceCandidate(data, peerId) {
        const peer = this.peers[peerId];

        if (!peer) {
            return;
        }

        try {
            await peer.addIceCandidate(new RTCIceCandidate(data.candidate));
            this.debugLog("handle_candidate", data);
        } catch (error) {
            console.log("Error adding ice candidate", error);
        }
    }

    async dispatchSignal(data) {
        this.debugLog("send_signal", data);
        await this.data.call("pos.config", "dispatch_rtc_signal", [
            odoo.pos_config_id,
            {
                login_number: odoo.login_number,
                rtc_params: data,
            },
        ]);
    }

    debugLog(type, data) {
        if (odoo.debug === "assets") {
            const { message, color } = DEBUG_COLOR_MESSAGE[type];
            console.debug(`%c[RTC Data channel] ${message}`, `color: ${color}`, data);
        }
    }
}
