import { rpc } from "@web/core/network/rpc";

const ORDERED_TRANSCEIVER_NAMES = ["audio", "screen", "camera"];
const PEER_NOTIFICATION_WAIT_DELAY = 50;
const RECOVERY_TIMEOUT = 15_000;
const INVALID_ICE_CONNECTION_STATES = new Set(["disconnected", "failed", "closed"]);
const IS_CLIENT_RTC_COMPATIBLE = Boolean(window.RTCPeerConnection && window.MediaStream);
const DEFAULT_ICE_SERVERS = [
    { urls: ["stun:stun1.l.google.com:19302", "stun:stun2.l.google.com:19302"] },
];

let tmpId = 0;

/**
 * TODO:
 * Sort functions, set public/private
 * error/recovery system
 *
 * NOTES: api similar to SFU
 * API:
 * connect(id): add one peer connection to that id, the API user must call it for each peer
 * disconnect(id): removes the peer connection of that id, the API user must call it for each peer when they have to be removed
 * updateUpload(track) + track label like SFU
 * updateDownload()
 * broadcast() the SFU does not have that feature yet sending arbitrary messages is not in the scope of discuss)
 * updateInfo()
 *
 * emits:
 * "update"
 * "stateChange" (with peer id in payload)
 *
 */

/**
 * @param {RTCPeerConnection} peerConnection
 * @param {String} trackKind
 * @returns {RTCRtpTransceiver} the transceiver used for this trackKind.
 */
function getTransceiver(peerConnection, trackKind) {
    const transceivers = peerConnection.getTransceivers();
    return transceivers[ORDERED_TRANSCEIVER_NAMES.indexOf(trackKind)];
}

/**
 * @param {RTCPeerConnection} peerConnection
 * @param {RTCRtpTransceiver} transceiver
 */
function getTransceiverType(peerConnection, transceiver) {
    const transceivers = peerConnection.getTransceivers();
    return ORDERED_TRANSCEIVER_NAMES[transceivers.indexOf(transceiver)];
}

export class Peer {
    /**
     * @type {number}
     */
    id;
    /**
     * @type {RTCPeerConnection}
     */
    connection;
    /**
     * @type {RTCDataChannel}
     */
    dataChannel;
    // TODO explicit state of broadcasting?
    // TODO state of whether we want to download their streams?

    /**
     * @param {number} id
     * @param {RTCPeerConnection} connection
     * @param {RTCDataChannel} dataChannel
     */
    constructor(id, connection, dataChannel) {
        this.id = id;
        this.connection = connection;
        this.dataChannel = dataChannel;
    }
}

export class PeerToPeer extends EventTarget {
    /**
     * @type {number}
     */
    _selfId;
    _iceServers = DEFAULT_ICE_SERVERS;
    _isPendingNotify = false;
    _notificationsToSend = new Map();
    /**
     * @type {Map<number, Peer>}
     */
    peers = new Map();
    notificationRoute = "/mail/rtc/session/notify_call_members";
    /**
     * @type {MediaStreamTrack}
     */
    _audioTrack;
    /**
     * @type {MediaStreamTrack}
     */
    _screenTrack;
    /**
     * @type {MediaStreamTrack}
     */
    _cameraTrack;
    canDownloadVideoFrom(id) {
        return true;
    }
    /**
     * @param {number} _selfId
     * @param {number} channelId
     * @param {object} options
     * @param {array} options._iceServers
     */
    constructor(_selfId, channelId, { _iceServers }) {
        super();
        if (!IS_CLIENT_RTC_COMPATIBLE) {
            throw new Error("RTCPeerConnection is not supported");
        }
        this._selfId = _selfId;
        this._iceServers = _iceServers || this._iceServers;
        this.channelId = channelId;
    }
    async broadcast(message) {
        await this._notify("broadcast", { payload: message });
    }
    async connect(id) {
        const peer = this._createConnection(id);
        for (const transceiverName of ORDERED_TRANSCEIVER_NAMES) {
            await this._updateRemote(peer, transceiverName);
        }
    }
    disconnect(id) {
        const peer = this.peers.get(id);
        if (!peer) {
            return;
        }
        if (peer.dataChannel) {
            peer.dataChannel.close();
        }
        if (peer.connection) {
            peer.connection.close();
        }
        this.peers.delete(id);
    }
    /**
     * Stop or resume the consumption of tracks from the other call participants.
     *
     * @param {number} id
     * @param {Object<[streamType, boolean]>} states e.g: { audio: true, camera: false }
     */
    updateDownload(id, states) {
        return [id, states];
    }
    /**
     * @param {streamType} type
     * @param {MediaStreamTrack | null} track track to be sent to the other call participants,
     * not setting it will remove the track from the server
     */
    updateUpload(type, track) {
        switch (type) {
            case "audio":
                this._audioTrack = track;
                break;
            case "screen":
                this._screenTrack = track;
                break;
            case "camera":
                this._cameraTrack = track;
                break;
        }
        // TODO probably need to update all remotes
    }
    updateInfo(info) {
        return info;
    }
    _recover(peer) {
        return peer;
    }
    async _sendNotifications() {
        if (this._isPendingNotify) {
            return;
        }
        this._isPendingNotify = true;
        await new Promise((resolve) => setTimeout(resolve, PEER_NOTIFICATION_WAIT_DELAY));
        const ids = [];
        const notifications = [];
        this._notificationsToSend.forEach((notification, id) => {
            ids.push(id);
            notifications.push([
                notification.sender,
                notification.targets,
                JSON.stringify({
                    event: notification.event,
                    channelId: notification.channelId,
                    payload: notification.payload,
                }),
            ]);
        });
        try {
            await rpc(
                this.notificationRoute,
                {
                    peer_notifications: notifications,
                },
                { silent: true }
            );
            for (const id of ids) {
                this._notificationsToSend.delete(id);
            }
        } finally {
            this._isPendingNotify = false;
            if (this._notificationsToSend.size > 0) {
                await this._sendNotifications();
            }
        }
    }
    /**
     * @param {String} event
     * @param {Object} options
     * @param {Object} [options.payload]
     * @param {number[]} [options.targets] list of the ids of peers to send the message to,
     * sends to all peers if no specified target(s)
     */
    async _notify(event, { payload, targets }) {
        targets = targets || [...this.peers.keys()];
        if (event === "trackChange") {
            // p2p
            for (const id of targets) {
                const peer = this.peers.get(id);
                if (!peer?.dataChannel || peer?.dataChannel.readyState !== "open") {
                    continue;
                }
                peer.dataChannel.send(
                    JSON.stringify({
                        event,
                        channelId: this.channelId,
                        payload,
                    })
                );
            }
        } else {
            // server
            this._notificationsToSend.set(++tmpId, {
                channelId: this.channelId,
                event,
                payload,
                sender: this._selfId,
                targets,
            });
            await this._sendNotifications();
        }
    }
    _getTransceiverDirection(peer, canUpload = false) {
        if (this.canDownloadVideoFrom(peer.id)) {
            return canUpload ? "sendrecv" : "recvonly";
        } else {
            return canUpload ? "sendonly" : "inactive";
        }
    }
    /**
     * Updates the track that is broadcast to the RTCPeerConnection.
     * This will start new transaction by triggering a negotiationneeded event
     * on the peerConnection given as parameter.
     *
     * negotiationneeded -> offer -> answer -> ...
     */
    async _updateRemote(peer, trackKind) {
        // log
        let track;
        switch (trackKind) {
            case "audio": {
                track = this._audioTrack;
                break;
            }
            case "camera": {
                track = this._cameraTrack;
                break;
            }
            case "screen": {
                track = this._screenTrack;
                break;
            }
        }
        let transceiverDirection = track ? "sendrecv" : "recvonly";
        if (trackKind !== "audio") {
            transceiverDirection = this._getTransceiverDirection(peer, Boolean(track));
        }
        const transceiver = getTransceiver(peer.connection, trackKind);
        try {
            await transceiver.sender.replaceTrack(track || null);
            transceiver.direction = transceiverDirection;
        } catch {
            // log `failed to update ${trackKind} transceiver`
        }
        if (!track && trackKind !== "audio") {
            await this._notify("trackChange", {
                payload: {
                    type: getTransceiverType(peer.connection, transceiver),
                },
                targets: [peer.id],
            });
        }
    }
    async _handleNotification(id, content) {
        const { event, payload } = JSON.parse(content);
        // log `received notification: ${event}`
        let peer = this.peers.get(id);
        if (!peer) {
            peer = this._createConnection(id);
            // TODO careful that we may create a peer for a stale ID, need to trigger an event so that it can be closed. Or use a callback to verify before creating it.
        }
        const pc = peer.connection;
        switch (event) {
            case "offer": {
                if (
                    INVALID_ICE_CONNECTION_STATES.has(pc.iceConnectionState) ||
                    pc.signalingState === "have-remote-offer"
                ) {
                    return;
                }
                const description = new window.RTCSessionDescription(payload.sdp);
                try {
                    await pc.setRemoteDescription(description);
                } catch {
                    // log "offer handling: failed at setting remoteDescription"
                    return;
                }
                if (pc.getTransceivers().length === 0) {
                    for (const trackKind of ORDERED_TRANSCEIVER_NAMES) {
                        const type = ["screen", "camera"].includes(trackKind) ? "video" : trackKind;
                        pc.addTransceiver(type);
                    }
                }
                for (const transceiverName of ORDERED_TRANSCEIVER_NAMES) {
                    await this._updateRemote(peer, transceiverName);
                }

                let answer;
                try {
                    answer = await pc.createAnswer();
                } catch {
                    // log "offer handling: failed at creating answer"
                    return;
                }
                try {
                    await pc.setLocalDescription(answer);
                } catch {
                    // log "offer handling: failed at setting localDescription"
                    return;
                }

                // log "sending notification: answer"
                await this._notify("answer", {
                    payload: {
                        sdp: pc.localDescription,
                    },
                    targets: [peer.id],
                });
                this._recover(peer, RECOVERY_TIMEOUT, "standard answer timeout");
                break;
            }
            case "answer": {
                // log `received notification: ${event}`
                if (
                    INVALID_ICE_CONNECTION_STATES.has(pc.iceConnectionState) ||
                    pc.signalingState === "stable" ||
                    pc.signalingState === "have-remote-offer"
                ) {
                    return;
                }
                const description = new window.RTCSessionDescription(payload.sdp);
                try {
                    await pc.setRemoteDescription(description);
                } catch {
                    // log "answer handling: Failed at setting remoteDescription"
                    // ignored the transaction may have been resolved by another concurrent offer.
                }
                break;
            }
            case "ice-candidate": {
                if (INVALID_ICE_CONNECTION_STATES.has(pc.iceConnectionState)) {
                    return;
                }
                const rtcIceCandidate = new window.RTCIceCandidate(payload.candidate);
                try {
                    await pc.addIceCandidate(rtcIceCandidate);
                } catch {
                    // log "ICE candidate handling: failed at adding the candidate to the connection"
                    this._recover(peer, RECOVERY_TIMEOUT, "failed at adding ice candidate");
                }
                break;
            }
            case "trackChange": {
                const payload = {}; // { id, type, track, active }
                // TODO reconcile using id, or peerId(p2p)/sessionId(sfu)
                // TODO this should use the same event system as SFU and be handled by `_handleSfuClientUpdates` (to rename)
                this.dispatchEvent(
                    new CustomEvent("update", { detail: { name: "track", payload } })
                );
                break;
            }
        }
    }
    /**
     * should be private?
     * @param {number} id
     * @returns {Peer}
     */
    _createConnection(id) {
        const record = this.peers.get(id);
        if (record) {
            this.disconnect(id);
        }
        const peerConnection = new window.RTCPeerConnection({ _iceServers: this._iceServers });
        peerConnection.onicecandidate = async (event) => {
            if (!event.candidate) {
                return;
            }
            await this._notify("ice-candidate", {
                payload: {
                    candidate: event.candidate,
                },
                targets: [id],
            });
        };
        peerConnection.oniceconnectionstatechange = async (event) => {
            switch (peerConnection.iceConnectionState) {
                case "closed":
                    this.disconnect(id);
                    break;
                case "failed":
                case "disconnected":
                    // RECOVER
                    break;
            }
        };
        peerConnection.onicegatheringstatechange = (event) => {
            //log
        };
        peerConnection.onconnectionstatechange = async (event) => {
            //log
        };
        peerConnection.onicecandidateerror = async (error) => {
            //log
            // RECOVER
        };
        peerConnection.onnegotiationneeded = async (event) => {
            const offer = await peerConnection.createOffer();
            try {
                await peerConnection.setLocalDescription(offer);
            } catch {
                //log
                return;
            }
            await this._notify("offer", {
                payload: {
                    sdp: peerConnection.localDescription,
                },
                targets: [id],
            });
        };
        peerConnection.ontrack = ({ transceiver, track }) => {
            //log
        };
        const dataChannel = peerConnection.createDataChannel("notifications", {
            negotiated: true,
            id: 1,
        });
        dataChannel.onmessage = async (event) => {
            await this._handleNotification(id, event.data);
        };
        dataChannel.onopen = async () => {
            await this._notify("trackChange", {
                payload: {
                    type: "audio",
                    state: {
                        isTalking: this.state.selfSession.isTalking,
                        isSelfMuted: this.state.selfSession.isSelfMuted,
                    },
                },
                targets: [peer.id],
            });
            this.dispatchEvent(new CustomEvent("connected", { detail: { id } }));
        };
        const peer = new Peer(id, peerConnection, dataChannel);
        this.peers.set(id, peer);
        return peer;
    }
}
