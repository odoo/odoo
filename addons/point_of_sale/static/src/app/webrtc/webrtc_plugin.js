import { Plugin, onWillDestroy, signal, useListener, usePlugin } from "@odoo/owl";
import { BusPlugin } from "@bus/services/bus_plugin";
import { rpc } from "@web/core/network/rpc";
import { services } from "@web/core/services";
import { getOnNotified, uuidv4 } from "@point_of_sale/utils";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

const CONSOLE_COLOR = "#7c4dff";

/**
 * Peer-to-peer connections between the terminals of a PoS config.
 *
 * The server only relays the signaling, on the bus channel of the config:
 * 1. a terminal that starts broadcasts an `announce`;
 * 2. for each pair of terminals, the one with the smaller id sends the `offer`
 *    (the other one answers the announce with its own, sent to the newcomer
 *    only), so two terminals never send an offer to each other at the same time;
 * 3. the other terminal replies with an `answer`, and the data channel opens.
 *
 * The network candidates are gathered before sending the offer and the answer,
 * so that they are part of the session description and need no message of
 * their own. No STUN server is used: the terminals are expected to be on the
 * same local network.
 */
export class WebRtcPlugin extends Plugin {
    bus = usePlugin(BusPlugin);
    /** Connection state of each peer, by peer id (shown in the debug widget). */
    peerStates = signal.Map(new Map());

    setup() {
        this.id = uuidv4();
        this.configId = null;
        /** @type {Map<string, {pc: RTCPeerConnection, channel: RTCDataChannel|null}>} */
        this.peers = new Map();

        useListener(window, "pagehide", () => this.stop());
        onWillDestroy(() => this.stop());
    }

    /**
     * @param {Object} params
     * @param {number} params.configId
     * @param {string} params.accessToken - access token of the config, i.e. its bus channel
     */
    async start({ configId, accessToken }) {
        this.configId = configId;
        const onNotified = getOnNotified(this.bus, accessToken);
        onNotified("WEBRTC_SIGNAL", (message) => this.onSignal(message));
        try {
            await this.announce();
        } catch (error) {
            console.error("[WebRTC] Failed to announce", error);
            return;
        }
        this.log("start", `Announced as ${this.id}`);
    }

    announce() {
        return this.signal({ type: "announce" });
    }

    stop() {
        for (const peerId of this.peers.keys()) {
            this.closePeer(peerId);
        }
    }

    /**
     * Sends a text to every connected terminal.
     */
    broadcast(text) {
        for (const { channel } of this.peers.values()) {
            if (channel?.readyState === "open") {
                channel.send(JSON.stringify({ type: "text", text }));
            }
        }
    }

    // ─── Signaling ────────────────────────────────────────────────────────────

    signal(message) {
        return rpc("/pos/webrtc/signal", {
            config_id: this.configId,
            message: { ...message, from: this.id },
        });
    }

    onSignal(message) {
        if (message.from === this.id || (message.to && message.to !== this.id)) {
            return;
        }
        switch (message.type) {
            case "announce":
                return this.onAnnounce(message);
            case "offer":
                return this.onOffer(message);
            case "answer":
                return this.onAnswer(message);
        }
    }

    onAnnounce({ from, to }) {
        if (this.id < from) {
            this.connect(from);
        } else if (!to) {
            // Let the newcomer send the offer, since its id is the smaller one.
            this.signal({ type: "announce", to: from });
        }
    }

    async connect(peerId) {
        this.closePeer(peerId);
        const pc = this.createPeer(peerId);
        this.setupChannel(peerId, pc.createDataChannel("pos"));
        await pc.setLocalDescription(await pc.createOffer());
        await waitIceGathering(pc);
        await this.signal({ type: "offer", to: peerId, sdp: pc.localDescription.toJSON() });
        this.log("connect", `Offer sent to ${peerId}`);
    }

    async onOffer({ from, sdp }) {
        this.closePeer(from);
        const pc = this.createPeer(from);
        pc.ondatachannel = ({ channel }) => this.setupChannel(from, channel);
        await pc.setRemoteDescription(sdp);
        await pc.setLocalDescription(await pc.createAnswer());
        await waitIceGathering(pc);
        await this.signal({ type: "answer", to: from, sdp: pc.localDescription.toJSON() });
        this.log("onOffer", `Answer sent to ${from}`);
    }

    async onAnswer({ from, sdp }) {
        const pc = this.peers.get(from)?.pc;
        if (pc?.signalingState === "have-local-offer") {
            await pc.setRemoteDescription(sdp);
        }
    }

    // ─── Peers ────────────────────────────────────────────────────────────────

    createPeer(peerId) {
        const pc = new RTCPeerConnection();
        pc.onconnectionstatechange = () => {
            this.peerStates().set(peerId, pc.connectionState);
            this.log("connectionState", `${peerId}: ${pc.connectionState}`);
            if (["failed", "closed"].includes(pc.connectionState)) {
                this.closePeer(peerId);
            }
        };
        this.peers.set(peerId, { pc, channel: null });
        this.peerStates().set(peerId, pc.connectionState);
        return pc;
    }

    setupChannel(peerId, channel) {
        const peer = this.peers.get(peerId);
        if (!peer) {
            return;
        }
        peer.channel = channel;
        channel.onopen = () => {
            this.log("channel", `Open with ${peerId}`);
            channel.send(JSON.stringify({ type: "text", text: `Hello world from ${this.id}` }));
        };
        channel.onmessage = ({ data }) => {
            const message = JSON.parse(data);
            this.log("message", `From ${peerId}: ${message.text}`);
        };
        channel.onclose = () => this.closePeer(peerId);
    }

    closePeer(peerId) {
        const peer = this.peers.get(peerId);
        if (!peer) {
            return;
        }
        this.peers.delete(peerId);
        this.peerStates().delete(peerId);
        peer.pc.onconnectionstatechange = null;
        if (peer.channel) {
            peer.channel.onclose = null;
            peer.channel.close();
        }
        peer.pc.close();
    }

    log(functionName, message) {
        logPosMessage("WebRTC", functionName, message, CONSOLE_COLOR);
        // `logPosMessage` only prints with exactly `debug=assets`.
        if (odoo.debug?.includes("webrtc")) {
            console.info(
                `%c[WebRTC]%c ${functionName} - ${message}`,
                `color:${CONSOLE_COLOR};`,
                ""
            );
        }
    }
}

function waitIceGathering(pc) {
    if (pc.iceGatheringState === "complete") {
        return Promise.resolve();
    }
    return new Promise((resolve) => {
        pc.addEventListener("icegatheringstatechange", () => {
            if (pc.iceGatheringState === "complete") {
                resolve();
            }
        });
    });
}

services.add(WebRtcPlugin);
