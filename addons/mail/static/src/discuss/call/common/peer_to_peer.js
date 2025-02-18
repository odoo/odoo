import { rpc } from "@web/core/network/rpc";
import { Deferred } from "@web/core/utils/concurrency";
import { browser } from "@web/core/browser/browser";

export const STREAM_TYPE = Object.freeze({
    AUDIO: "audio",
    CAMERA: "camera",
    SCREEN: "screen",
});
export const UPDATE_EVENT = Object.freeze({
    BROADCAST: "broadcast",
    CONNECTION_CHANGE: "connection_change",
    DISCONNECT: "disconnect",
    INFO_CHANGE: "info_change",
    TRACK: "track",
});
const LOG_LEVEL = Object.freeze({
    NONE: "none",
    DEBUG: "debug",
    INFO: "info",
    WARN: "warn",
    ERROR: "error",
});
const INTERNAL_EVENT = Object.freeze({
    ANSWER: "answer",
    BROADCAST: "broadcast",
    DISCONNECT: "disconnect",
    ICE_CANDIDATE: "ice-candidate",
    INFO: "info",
    OFFER: "offer",
    TRACK_CHANGE: "trackChange",
});
const ORDERED_TRANSCEIVER_TYPES = [STREAM_TYPE.AUDIO, STREAM_TYPE.CAMERA, STREAM_TYPE.SCREEN];
const DEFAULT_BUS_BATCH_DELAY = 100;
const INITIAL_RECONNECT_DELAY = 2_000 + Math.random() * 1_000; // the initial delay between reconnection attempts
const MAXIMUM_RECONNECT_DELAY = 25_000 + Math.random() * 5_000; // the longest delay possible between reconnection attempts
const INVALID_ICE_CONNECTION_STATES = new Set(["disconnected", "failed", "closed"]);
const IS_CLIENT_RTC_COMPATIBLE = Boolean(window.RTCPeerConnection && window.MediaStream);
const DEFAULT_ICE_SERVERS = [
    { urls: ["stun:stun1.l.google.com:19302", "stun:stun2.l.google.com:19302"] },
];
const DEFAULT_NOTIFICATION_ROUTE = "/mail/rtc/session/notify_call_members";

/**
 * @typedef {Object} Media
 * @property {MediaStreamTrack | null} track the track of the associated RtcRtpTransceiver, its presence does not
 *     imply active streaming as it exists for the whole lifetime transceiver (since webRTC 'unified plan').
 * @property {boolean} active represents whether the remote (peer) is actively streaming this track
 * @property {boolean} accepted represents whether the local (current user) wants to download this track
 */

/**
 * @typedef {Object} Info (sealed)
 * @property {boolean} isSelfMuted
 * @property {boolean} isRaisingHand
 * @property {boolean} isDeaf
 * @property {boolean} isTalking
 * @property {boolean} isCameraOn
 * @property {boolean} isScreenSharingOn
 */

export class Peer {
    /** @type {number} */
    id;
    /** @type {RTCPeerConnection} */
    connection;
    /** @type {number} */
    connectRetryDelay = INITIAL_RECONNECT_DELAY;
    /** @type {RTCDataChannel} */
    dataChannel;
    hasPriority = false;
    isBuildingOffer = false;
    isBuildingAnswer = false;
    /** @type {Object<STREAM_TYPE[keyof STREAM_TYPE], Media>} */
    medias = Object.seal({
        [STREAM_TYPE.AUDIO]: {
            track: null,
            active: false,
            accepted: true,
        },
        [STREAM_TYPE.SCREEN]: {
            track: null,
            active: false,
            accepted: true,
        },
        [STREAM_TYPE.CAMERA]: {
            track: null,
            active: false,
            accepted: true,
        },
    });
    /**
     * @param {number} id
     * @param {Object} param2
     * @param {RTCPeerConnection} param2.connection
     * @param {RTCDataChannel} param2.dataChannel
     * @param {boolean} hasPriority true if this peer offers should have priority in case of collisions
     * @param {number} [connectRetryDelay=INITIAL_RECONNECT_DELAY]
     */
    constructor(
        id,
        {
            connection,
            dataChannel,
            hasPriority = false,
            connectRetryDelay = INITIAL_RECONNECT_DELAY,
        }
    ) {
        this.id = id;
        this.connection = connection;
        this.dataChannel = dataChannel;
        this.hasPriority = hasPriority;
        this.connectRetryDelay = connectRetryDelay;
        this.ready = new Deferred();
    }

    disconnect() {
        if (this.connection) {
            const RTCRtpSenders = this.connection.getSenders();
            for (const sender of RTCRtpSenders) {
                try {
                    this.connection.removeTrack(sender);
                } catch {
                    // ignore error
                }
            }
            for (const transceiver of this.connection.getTransceivers()) {
                try {
                    transceiver.stop();
                } catch {
                    // transceiver may already be stopped by the remote.
                }
            }
        }
        this.ready.resolve?.();
        this.connection?.close();
        this.connection = undefined;
        this.dataChannel?.close();
        this.dataChannel = undefined;
        for (const media of Object.values(this.medias)) {
            media.track?.stop();
        }
    }
    /**
     * @param {{STREAM_TYPE[keyof STREAM_TYPE]}} streamType
     * @param {boolean} canUpload whether this transceiver needs upload capability (outbound stream)
     * @returns {RTCRtpTransceiverDirection}
     */
    getRecommendedTransceiverDirection(streamType, canUpload = false) {
        if (this.medias[streamType].accepted) {
            return canUpload ? "sendrecv" : "recvonly";
        } else {
            return canUpload ? "sendonly" : "inactive";
        }
    }
    /**
     * @param {STREAM_TYPE[keyof STREAM_TYPE]} streamType
     * @returns {RTCRtpTransceiver | undefined} the transceiver used for this trackKind.
     */
    getTransceiver(streamType) {
        if (!this.connection) {
            // may be disconnected
            return;
        }
        const transceivers = this.connection.getTransceivers();
        return transceivers[ORDERED_TRANSCEIVER_TYPES.indexOf(streamType)];
    }
    /**
     * @param {RTCRtpTransceiver} transceiver
     * @returns {STREAM_TYPE[keyof STREAM_TYPE]}
     */
    getTransceiverStreamType(transceiver) {
        const transceivers = this.connection.getTransceivers();
        return ORDERED_TRANSCEIVER_TYPES[transceivers.indexOf(transceiver)];
    }
}

/**
 * This class represents a network of peers and handles peer to peer connections.
 *
 *  @fires PeerToPeer#update
 */
export class PeerToPeer extends EventTarget {
    /** @type {number} */
    selfId;
    /** @type {number}*/
    channelId;
    /** @type {Map<number, Peer>}*/
    peers = new Map();
    /** @type {number} */
    _batchDelay = DEFAULT_BUS_BATCH_DELAY;
    /** @type {Info} */
    _localInfo = Object.seal({
        isSelfMuted: false,
        isRaisingHand: false,
        isDeaf: false,
        isTalking: false,
        isCameraOn: false,
        isScreenSharingOn: false,
    });
    /** @type {String[]} */
    _iceServers;
    _isPendingNotify = false;
    _notificationsToSend = new Map();
    _isAntiGlareEnabled = true;
    /**
     * id of notification transaction
     * @type {number}
     */
    _tmpNotificationId = 0;
    /**
     * by peer ID
     * @type {Map<timeoutID>}
     */
    _recoverTimeouts = new Map();
    /** @type {String} */
    _notificationRoute;
    /** @type {boolean} */
    _isStreamingEnabled = true;
    /** @type {Object<STREAM_TYPE[keyof STREAM_TYPE], MediaStreamTrack | null>} */
    _tracks = Object.seal({
        [STREAM_TYPE.AUDIO]: null,
        [STREAM_TYPE.SCREEN]: null,
        [STREAM_TYPE.CAMERA]: null,
    });
    _loggingFunctions = {
        [LOG_LEVEL.DEBUG]: () => {},
        [LOG_LEVEL.INFO]: () => {},
        [LOG_LEVEL.WARN]: () => {},
        [LOG_LEVEL.ERROR]: () => {},
    };
    get isActive() {
        return Boolean(this.selfId !== undefined && this.channelId !== undefined);
    }
    /**
     * @param {object} [options]
     * @param {String} [options.notificationRoute] the route used to communicate with the odoo server
     * @param {LOG_LEVEL[keyof LOG_LEVEL]} [options.logLevel=LOG_LEVEL.NONE]
     * @param {boolean} [options.antiGlare=true] whether or not to use the rollback feature to manage offer collisions,
     *        ids provided for peers should be comparable for this feature to work.
     * @param {number} [options.batchDelay=DEFAULT_BUS_BATCH_DELAY]
     * @param {boolean} [options.enableStreaming=true] whether or not setting the peer connections with audio and video
     *        transceivers to allow streaming features.
     */
    constructor({
        notificationRoute = DEFAULT_NOTIFICATION_ROUTE,
        logLevel = LOG_LEVEL.WARN,
        batchDelay = DEFAULT_BUS_BATCH_DELAY,
        antiGlare = true,
        enableStreaming = true,
    } = {}) {
        super();
        this._isStreamingEnabled = enableStreaming;
        this._isAntiGlareEnabled = antiGlare;
        this._notificationRoute = notificationRoute;
        this._batchDelay = batchDelay;
        this.setLoggingLevel(logLevel);
    }

    /**
     * @param {any} selfId should be comparable to benefit from the anti glare (offer collisions)
     * @param {any} channelId
     * @param {object} [options]
     * @param {Info} [options.info={}]
     * @param {array} [options.iceServers=DEFAULT_ICE_SERVERS]
     */
    connect(selfId, channelId, { info = {}, iceServers = DEFAULT_ICE_SERVERS } = {}) {
        if (!IS_CLIENT_RTC_COMPATIBLE) {
            throw new Error("RTCPeerConnection is not supported");
        }
        this.selfId = selfId;
        this.channelId = channelId;
        this._iceServers = iceServers;
        this._localInfo = Object.assign(this._localInfo, info);
    }

    removeALlPeers() {
        for (const peer of this.peers.values()) {
            this.removePeer(peer.id);
        }
        this.peers.clear();
    }

    disconnect() {
        this.removeALlPeers();
        this.selfId = undefined;
        this.channelId = undefined;
        this._isPendingNotify = false;
        this._notificationsToSend.clear();
        this._localInfo = Object.assign(this._localInfo, {
            isSelfMuted: false,
            isRaisingHand: false,
            isDeaf: false,
            isTalking: false,
            isCameraOn: false,
            isScreenSharingOn: false,
        });
    }
    /**
     * Adds a peer and starts the process of connection establishment. From this point the whole
     * peer lifecycle is handled internally, including connection recovery attempts, until
     * `removePeer()` or `disconnect()` is called.
     * If a peer of that id already exists, it is returned without being re-created.
     * This allows `addPeer` to be called to ensure that all of them are registered without fear
     * of resetting connections (removePeer() should be called explicitly if that is the intention).
     *
     * @param {number} id
     * @param {object} [options={}] options for the Peer constructor
     * @returns {Peer} resolved when the dataChannel is open
     */
    async addPeer(id, options = {}) {
        const peer = this.peers.get(id);
        if (peer) {
            return peer;
        }
        const newPeer = this._createPeer(id, options);
        await newPeer.ready;
        return newPeer;
    }
    removePeer(id) {
        const recoverTimeoutId = this._recoverTimeouts.get(id);
        browser.clearTimeout(recoverTimeoutId);
        this._recoverTimeouts.delete(id);
        const peer = this.peers.get(id);
        if (!peer) {
            return;
        }
        this.peers.delete(id);
        peer.disconnect();
    }

    /**
     * Broadcast a message to all peers
     * @param message any JSON serializable
     */
    broadcast(message) {
        this._dataChannelBroadcast(INTERNAL_EVENT.BROADCAST, message);
    }
    /**
     * @param id
     * @return {{
     *     connectionState: RTCPeerConnection.connectionState
     *     iceConnectionState: RTCPeerConnection.iceConnectionState
     *     iceGatheringState: RTCPeerConnection.iceGatheringState
     *     localCandidateType: RTCIceCandidatePairStats.candidateType
     *     remoteCandidateType: RTCIceCandidatePairStats.candidateType
     *     dataChannelState:  RTCDataChannelStats.state
     *     dtlsState: RTCTransportStats.dtpsState,
     *     iceState: RTCTransportStats.iceState,
     *     packetsReceived: RTCTransportStats.packetsReceived,
     *     packetsSent: RTCTransportStats.packetsSent,
     * } | {}}
     */
    async getFormattedStats(id) {
        const peer = this.peers.get(id);
        const formattedStats = {};
        if (!peer) {
            return formattedStats;
        }
        formattedStats.connectionState = peer.connection.connectionState;
        formattedStats.iceConnectionState = peer.connection.iceConnectionState;
        formattedStats.iceGatheringState = peer.connection.iceGatheringState;
        const stats = await peer.connection.getStats();
        for (const value of stats?.values() || []) {
            switch (value.type) {
                case "candidate-pair":
                    if (value.state === "succeeded" && value.localCandidateId) {
                        formattedStats.localCandidateType =
                            stats.get(value.localCandidateId)?.candidateType || "";
                        formattedStats.remoteCandidateType =
                            stats.get(value.remoteCandidateId)?.candidateType || "";
                    }
                    break;
                case "data-channel":
                    formattedStats.dataChannelState = value.state;
                    break;
                case "transport":
                    formattedStats.dtlsState = value.dtlsState;
                    formattedStats.iceState = value.iceState;
                    formattedStats.packetsReceived = value.packetsReceived;
                    formattedStats.packetsSent = value.packetsSent;
                    break;
            }
        }
        return formattedStats;
    }
    /**
     * Stop or resume the consumption of tracks from the other call participants.
     *
     * @param {number} id
     * @param {Object<[STREAM_TYPE[keyof STREAM_TYPE], boolean]>} states e.g: { screen: true, camera: false }
     */
    updateDownload(id, states) {
        const peer = this.peers.get(id);
        if (!peer) {
            return;
        }
        for (const [streamType, accepted] of Object.entries(states)) {
            peer.medias[streamType].accepted = accepted;
            const transceiver = peer.getTransceiver(streamType);
            if (!transceiver) {
                this._recover(id, `no transceiver available when updating direction`);
                return;
            }
            // changing the direction triggers a negotiation-needed
            transceiver.direction = peer.getRecommendedTransceiverDirection(
                streamType,
                Boolean(this._tracks[streamType])
            );
        }
    }

    /**
     * @param {STREAM_TYPE[keyof STREAM_TYPE]} streamType
     * @param {MediaStreamTrack | null} [track] track to be sent to the other call participants
     */
    async updateUpload(streamType, track) {
        this._tracks[streamType] = track || null;
        this.updateInfo({
            isScreenSharingOn: Boolean(this._tracks[STREAM_TYPE.SCREEN]),
            isCameraOn: Boolean(this._tracks[STREAM_TYPE.CAMERA]),
        });
        const proms = [];
        for (const peer of this.peers.values()) {
            proms.push(peer.ready.then(() => this._updateRemote(peer, streamType)));
        }
        await Promise.all(proms);
    }
    /**
     * @param {Info} info
     */
    updateInfo(info) {
        this._localInfo = Object.assign(this._localInfo, info);
        this._dataChannelBroadcast(INTERNAL_EVENT.INFO, this._localInfo);
    }
    /**
     * @param id id of the peer sending the notification
     * @param {string} content JSON
     */
    async handleNotification(id, content) {
        /** @type {{ event: INTERNAL_EVENT[keyof INTERNAL_EVENT], channelId, payload: Object }} */
        const { event, channelId, payload } = JSON.parse(content);
        this._emitLog(id, `received notification: ${event}`, LOG_LEVEL.DEBUG);
        if (channelId !== this.channelId) {
            return;
        }
        let peer = this.peers.get(id);
        if (event !== INTERNAL_EVENT.OFFER && !peer?.connection) {
            this._emitLog(id, `received ${event} for missing peer ${id}`, LOG_LEVEL.WARN);
            return;
        }
        switch (event) {
            case INTERNAL_EVENT.ANSWER: {
                this._emitLog(id, `received answer`, LOG_LEVEL.DEBUG);
                if (
                    INVALID_ICE_CONNECTION_STATES.has(peer.connection.iceConnectionState) ||
                    peer.connection.signalingState === "stable" ||
                    peer.connection.signalingState === "have-remote-offer"
                ) {
                    return;
                }
                const description = new window.RTCSessionDescription(payload.sdp);
                try {
                    await peer.connection.setRemoteDescription(description);
                } catch {
                    this._recover(id, "answer handling: Failed at setting remoteDescription");
                    // ignored the transaction may have been resolved by another concurrent offer.
                }
                break;
            }
            case INTERNAL_EVENT.BROADCAST: {
                this._emitUpdate({
                    name: UPDATE_EVENT.BROADCAST,
                    payload: { senderId: id, message: payload },
                });
                break;
            }
            case INTERNAL_EVENT.DISCONNECT: {
                this.removePeer(id);
                this._emitUpdate({ name: UPDATE_EVENT.DISCONNECT, payload: { sessionId: id } });
                break;
            }
            case INTERNAL_EVENT.ICE_CANDIDATE: {
                if (INVALID_ICE_CONNECTION_STATES.has(peer.connection.iceConnectionState)) {
                    return;
                }
                const rtcIceCandidate = new window.RTCIceCandidate(payload.candidate);
                try {
                    await peer.connection.addIceCandidate(rtcIceCandidate);
                } catch {
                    this._recover(id, "failed at adding ice candidate");
                }
                break;
            }
            case INTERNAL_EVENT.INFO: {
                const { isTalking, isCameraOn, isScreenSharingOn } = payload;
                peer.medias[STREAM_TYPE.AUDIO].active = isTalking;
                peer.medias[STREAM_TYPE.CAMERA].active = isCameraOn;
                peer.medias[STREAM_TYPE.SCREEN].active = isScreenSharingOn;
                this._emitUpdate({
                    name: UPDATE_EVENT.INFO_CHANGE,
                    payload: { [id]: payload },
                });
                break;
            }
            case INTERNAL_EVENT.OFFER: {
                if (!peer) {
                    peer = this._createPeer(id);
                }
                if (
                    INVALID_ICE_CONNECTION_STATES.has(peer.connection.iceConnectionState) ||
                    peer.connection.signalingState === "have-remote-offer"
                ) {
                    return;
                }
                const isStable =
                    peer.connection.signalingState === "stable" || peer.isBuildingAnswer;
                const hasOfferCollision = !isStable || peer.isBuildingOffer;
                if (hasOfferCollision && peer.hasPriority && this._isAntiGlareEnabled) {
                    this._emitLog(
                        peer.id,
                        `rolling back due to offer collision: ${peer.connection.signalingState}`,
                        LOG_LEVEL.WARN
                    );
                    try {
                        await peer.connection.setLocalDescription({ type: "rollback" });
                    } catch {
                        this._recover(id, `failed rollback`);
                    }
                }
                const description = new window.RTCSessionDescription(payload.sdp);
                try {
                    await peer.connection.setRemoteDescription(description);
                } catch {
                    this._recover(id, "failed at setting remoteDescription");
                    return;
                }
                if (this._isStreamingEnabled) {
                    if (peer.connection.getTransceivers().length === 0) {
                        for (const streamType of ORDERED_TRANSCEIVER_TYPES) {
                            const type = streamType === STREAM_TYPE.AUDIO ? "audio" : "video";
                            peer.connection.addTransceiver(type);
                        }
                    }
                    for (const transceiverName of ORDERED_TRANSCEIVER_TYPES) {
                        await this._updateRemote(peer, transceiverName);
                    }
                }
                peer.isBuildingAnswer = true;
                try {
                    await peer.connection.setLocalDescription(await peer.connection.createAnswer());
                } catch {
                    peer.isBuildingAnswer = false;
                    this._recover(id, "offer handling: failed at setting answer localDescription");
                    return;
                }
                peer.isBuildingAnswer = false;
                if (!this.isActive) {
                    return;
                }
                this._emitLog(id, `sending answer`, LOG_LEVEL.DEBUG);
                await this._busNotify(INTERNAL_EVENT.ANSWER, {
                    payload: {
                        sdp: peer.connection.localDescription,
                    },
                    targets: [peer.id],
                });
                this._recover(peer.id, "standard answer timeout");
                break;
            }
        }
    }
    /**
     * @param {LOG_LEVEL[keyof LOG_LEVEL]} logLevel
     */
    setLoggingLevel(logLevel) {
        const makeLog = (level) => {
            return (id, message) => {
                this.dispatchEvent(new CustomEvent("log", { detail: { id, level, message } }));
            };
        };
        this._loggingFunctions = {
            [LOG_LEVEL.DEBUG]: () => {},
            [LOG_LEVEL.INFO]: () => {},
            [LOG_LEVEL.WARN]: () => {},
            [LOG_LEVEL.ERROR]: () => {},
        };
        switch (logLevel) {
            case LOG_LEVEL.DEBUG:
                this._loggingFunctions[LOG_LEVEL.DEBUG] = makeLog(LOG_LEVEL.DEBUG);
            // eslint-disable-next-line no-fallthrough
            case LOG_LEVEL.INFO:
                this._loggingFunctions[LOG_LEVEL.INFO] = makeLog(LOG_LEVEL.INFO);
            // eslint-disable-next-line no-fallthrough
            case LOG_LEVEL.WARN:
                this._loggingFunctions[LOG_LEVEL.WARN] = makeLog(LOG_LEVEL.WARN);
            // eslint-disable-next-line no-fallthrough
            case LOG_LEVEL.ERROR:
                this._loggingFunctions[LOG_LEVEL.ERROR] = makeLog(LOG_LEVEL.ERROR);
        }
    }
    /**
     * @param {INTERNAL_EVENT[keyof INTERNAL_EVENT]} internalEvent
     * @param message any JSON serializable
     */
    _dataChannelBroadcast(internalEvent, message) {
        for (const peer of this.peers.values()) {
            if (!peer?.dataChannel || peer?.dataChannel.readyState !== "open") {
                continue;
            }
            peer.dataChannel.send(
                JSON.stringify({
                    event: internalEvent,
                    channelId: this.channelId,
                    payload: message,
                })
            );
        }
    }
    /**
     * @param {any} detail
     */
    _emitUpdate(detail) {
        this.dispatchEvent(new CustomEvent("update", { detail }));
    }
    /**
     * @param id
     * @param {string} message
     * @param {LOG_LEVEL[keyof LOG_LEVEL]} [level=LOG_LEVEL.DEBUG]
     */
    _emitLog(id, message, level = LOG_LEVEL.DEBUG) {
        this._loggingFunctions[level](id, message);
    }
    /**
     * @param id
     * @param {string} reason
     */
    _recover(id, reason = "") {
        this._emitLog(id, `connection recovery candidate: ${reason}`, LOG_LEVEL.WARN);
        if (this._recoverTimeouts.get(id)) {
            return;
        }
        const peer = this.peers.get(id);
        if (!peer) {
            return;
        }
        // Retry connecting with an exponential backoff.
        const delay =
            Math.min(peer.connectRetryDelay * 1.5, MAXIMUM_RECONNECT_DELAY) + 1000 * Math.random();
        this._recoverTimeouts.set(
            id,
            browser.setTimeout(async () => {
                const peer = this.peers.get(id);
                this._recoverTimeouts.delete(id);
                const connectionSuccess =
                    peer.connection.connectionState === "connected" ||
                    peer.connection.connectionState === "completed";
                const iceSuccess =
                    peer.connection.iceConnectionState === "connected" ||
                    peer.connection.iceConnectionState === "completed";
                if (!peer?.connection || !this.channelId || (connectionSuccess && iceSuccess)) {
                    return;
                }
                this._emitLog(id, `attempting to recover connection: ${reason}`, LOG_LEVEL.ERROR);
                this._busNotify(INTERNAL_EVENT.DISCONNECT, { targets: [peer.id] });
                this.removePeer(peer.id);
                this.addPeer(peer.id, { connectRetryDelay: delay });
            }, delay)
        );
    }
    async _sendNotifications() {
        if (this._isPendingNotify) {
            return;
        }
        this._isPendingNotify = true;
        await new Promise((resolve) => setTimeout(resolve, this._batchDelay));
        if (!this.isActive) {
            this._isPendingNotify = false;
            return;
        }
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
                this._notificationRoute,
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
     * @param {INTERNAL_EVENT[keyof INTERNAL_EVENT]} event
     * @param {Object} [options]
     * @param {Object} [options.payload]
     * @param {number[]} [options.targets] list of the ids of peers to send the message to,
     * sends to all peers if no specified target(s)
     */
    async _busNotify(event, { payload, targets } = {}) {
        targets = targets || Array.from(this.peers.keys());
        let id;
        if (event === INTERNAL_EVENT.OFFER) {
            // offers are always single-target, ensures that only 1 offer (the latest) per target is kept
            id = `latestOffer_to:${targets[0]}`;
        } else {
            id = ++this._tmpNotificationId;
        }
        this._notificationsToSend.set(id, {
            channelId: this.channelId,
            event,
            payload,
            sender: this.selfId,
            targets,
        });
        await this._sendNotifications();
    }
    /**
     * @param {Peer} peer
     * @param {STREAM_TYPE[keyof STREAM_TYPE]} streamType
     */
    async _updateRemote(peer, streamType) {
        const track = this._tracks[streamType];
        const transceiver = peer.getTransceiver(streamType);
        if (!transceiver) {
            return;
        }
        try {
            await transceiver.sender.replaceTrack(track);
            transceiver.direction = peer.getRecommendedTransceiverDirection(
                streamType,
                Boolean(track)
            );
        } catch (error) {
            this._recover(
                peer.id,
                `failed to update ${streamType} transceiver for peer ${peer.id}: ${error}`
            );
        }
    }
    /**
     * Creates a new peer.
     * If a peer of this id already exists, it is cleared.
     *
     * @param {number} id
     * @param {object} [options={}]
     * @returns {Peer}
     */
    _createPeer(id, options = {}) {
        this.removePeer(id);
        const peerConnection = new window.RTCPeerConnection({ iceServers: this._iceServers });
        const dataChannel = peerConnection.createDataChannel("notifications", {
            negotiated: true,
            id: 1,
        });
        const peer = new Peer(id, {
            ...options,
            connection: peerConnection,
            dataChannel,
            hasPriority: id > this.selfId,
        });
        this._emitUpdate({
            name: UPDATE_EVENT.CONNECTION_CHANGE,
            payload: { id, peer, state: "searching for network" },
        });
        this.peers.set(id, peer);
        peerConnection.addEventListener("icecandidate", async (event) => {
            if (!event.candidate) {
                return;
            }
            if (!this.isActive) {
                return;
            }
            await this._busNotify(INTERNAL_EVENT.ICE_CANDIDATE, {
                payload: {
                    candidate: event.candidate,
                },
                targets: [id],
            });
        });
        peerConnection.addEventListener("iceconnectionstatechange", async () => {
            switch (peerConnection.iceConnectionState) {
                case "closed":
                    this.removePeer(id);
                    break;
                case "failed":
                case "disconnected":
                    this._recover(peer.id, 1000, "ice connection disconnected");
                    break;
            }
        });
        peerConnection.addEventListener("icegatheringstatechange", () => {
            this._emitLog(
                id,
                `gathering state change: ${peerConnection.iceGatheringState}`,
                LOG_LEVEL.INFO
            );
        });
        peerConnection.addEventListener("connectionstatechange", async () => {
            this._emitUpdate({
                name: UPDATE_EVENT.CONNECTION_CHANGE,
                payload: { id, peer, state: peerConnection.connectionState },
            });
            switch (peerConnection.connectionState) {
                case "closed":
                    this.removePeer(id);
                    break;
                case "failed":
                case "disconnected":
                    this._recover(peer.id, 1000, "connection disconnected");
                    break;
            }
            this._emitLog(
                id,
                `connection state change: ${peerConnection.connectionState}`,
                LOG_LEVEL.INFO
            );
        });
        peerConnection.addEventListener("icecandidateerror", async (error) => {
            this._recover(id, `ice candidate error: ${error.errorText}`);
        });
        peerConnection.addEventListener("negotiationneeded", async () => {
            peer.isBuildingOffer = true;
            try {
                await peerConnection.setLocalDescription(await peerConnection.createOffer());
            } catch (error) {
                this._recover(id, `failed to set local Description for offer: ${error}`);
                peer.isBuildingOffer = false;
                return;
            }
            peer.isBuildingOffer = false;
            if (!this.isActive) {
                return;
            }
            await this._busNotify(INTERNAL_EVENT.OFFER, {
                payload: {
                    sdp: peerConnection.localDescription,
                },
                targets: [id],
            });
        });
        peerConnection.addEventListener("track", ({ transceiver, track }) => {
            if (!peer?.id || !this.peers.has(peer.id)) {
                return;
            }
            const streamType = peer.getTransceiverStreamType(transceiver);
            if (!streamType) {
                this._recover(id, "received track for unknown transceiver");
                return;
            }
            peer.medias[streamType].track = track;
            this._emitUpdate({
                name: UPDATE_EVENT.TRACK,
                payload: {
                    sessionId: id,
                    type: streamType,
                    track,
                    active: peer.medias[streamType].active,
                },
            });
        });
        dataChannel.addEventListener("message", async (event) => {
            await this.handleNotification(id, event.data);
        });
        dataChannel.addEventListener("open", () => {
            if (dataChannel.readyState !== "open") {
                // can be closed by the time the event is emitted
                return;
            }
            peer.ready.resolve();
            dataChannel.send(
                JSON.stringify({
                    event: INTERNAL_EVENT.INFO,
                    channelId: this.channelId,
                    payload: this._localInfo,
                })
            );
        });
        return peer;
    }
}
