const urlParams = new URLSearchParams(window.location.search);
const collaborationDebug = urlParams.get("collaborationDebug");
const COLLABORATION_LOCALSTORAGE_KEY = "odoo_editor_collaboration_debug";
if (typeof collaborationDebug === "string") {
    if (collaborationDebug === "false") {
        localStorage.removeItem(
            COLLABORATION_LOCALSTORAGE_KEY,
            urlParams.get("collaborationDebug")
        );
    } else {
        localStorage.setItem(COLLABORATION_LOCALSTORAGE_KEY, urlParams.get("collaborationDebug"));
    }
}
const debugValue = localStorage.getItem(COLLABORATION_LOCALSTORAGE_KEY);

const debugShowLog = ["", "true", "all"].includes(debugValue);
const debugShowNotifications = debugValue === "all";

const baseNotificationMethods = {
    ptp_request: async function (notification) {
        const { requestId, requestName, requestPayload, requestTransport } =
            notification.notificationPayload;
        this._onRequest(
            notification.fromPeerId,
            requestId,
            requestName,
            requestPayload,
            requestTransport
        );
    },
    ptp_request_result: function (notification) {
        const { requestId, result } = notification.notificationPayload;
        // If not in _pendingRequestResolver, it means it has timeout.
        if (this._pendingRequestResolver[requestId]) {
            clearTimeout(this._pendingRequestResolver[requestId].rejectTimeout);
            this._pendingRequestResolver[requestId].resolve(result);
            delete this._pendingRequestResolver[requestId];
        }
    },

    ptp_join: async function (notification) {
        const peerId = notification.fromPeerId;
        if (this.peersInfos[peerId] && this.peersInfos[peerId].peerConnection) {
            return this.peersInfos[peerId];
        }
        this._createPeer(peerId);
    },

    rtc_signal_icecandidate: async function (notification) {
        if (debugShowLog) {
            console.log(`%creceive candidate`, "background: darkgreen; color: white;");
        }
        const peerInfos = this.peersInfos[notification.fromPeerId];
        if (
            !peerInfos ||
            !peerInfos.peerConnection ||
            peerInfos.peerConnection.connectionState === "closed"
        ) {
            console.groupCollapsed("=== ERROR: Handle Ice Candidate from undefined|closed ===");
            console.trace(peerInfos);
            console.groupEnd();
            return;
        }
        if (!peerInfos.peerConnection.remoteDescription) {
            peerInfos.iceCandidateBuffer.push(notification.notificationPayload);
        } else {
            this._addIceCandidate(peerInfos, notification.notificationPayload);
        }
    },
    rtc_signal_description: async function (notification) {
        const description = notification.notificationPayload;
        if (debugShowLog) {
            console.log(
                `%cdescription received:`,
                "background: blueviolet; color: white;",
                description
            );
        }

        const peerInfos =
            this.peersInfos[notification.fromPeerId] || this._createPeer(notification.fromPeerId);
        const pc = peerInfos.peerConnection;

        if (!pc || pc.connectionState === "closed") {
            if (debugShowLog) {
                console.groupCollapsed("=== ERROR: handle offer ===");
                console.log(
                    "An offer has been received for a non-existent peer connection - peer: " +
                        notification.fromPeerId
                );
                console.trace(pc && pc.connectionState);
                console.groupEnd();
            }
            return;
        }

        // Skip if we already have an offer.
        if (pc.signalingState === "have-remote-offer") {
            return;
        }

        // If there is a racing conditing with the signaling offer (two
        // being sent at the same time). We need one peer that abort by
        // rollbacking to a stable signaling state where the other is
        // continuing the process. The peer that is polite is the one that
        // will rollback.
        const isPolite =
            ("" + notification.fromPeerId).localeCompare("" + this._currentPeerId) === 1;
        if (debugShowLog) {
            console.log(
                `%cisPolite: %c${isPolite}`,
                "background: deepskyblue;",
                `background:${isPolite ? "green" : "red"}`
            );
        }

        const isOfferRacing =
            description.type === "offer" &&
            (peerInfos.makingOffer || pc.signalingState !== "stable");
        // If there is a racing conditing with the signaling offer and the
        // peer is impolite, we must not process this offer and wait for
        // the answer for the signaling process to continue.
        if (isOfferRacing && !isPolite) {
            if (debugShowLog) {
                console.log(
                    `%creturn because isOfferRacing && !isPolite. pc.signalingState: ${pc.signalingState}`,
                    "background: red;"
                );
            }
            return;
        }
        if (debugShowLog) {
            console.log(`%cisOfferRacing: ${isOfferRacing}`, "background: red;");
            console.log(`%c SETREMOTEDESCRIPTION`, "background: navy; color:white;");
        }
        try {
            await pc.setRemoteDescription(description);
        } catch (e) {
            if (e instanceof DOMException && e.name === "InvalidStateError") {
                console.error(e);
                return;
            } else {
                throw e;
            }
        }
        if (peerInfos.iceCandidateBuffer.length) {
            for (const candidate of peerInfos.iceCandidateBuffer) {
                await this._addIceCandidate(peerInfos, candidate);
            }
            peerInfos.iceCandidateBuffer.splice(0);
        }
        if (description.type === "offer") {
            const answerDescription = await pc.createAnswer();
            try {
                await pc.setLocalDescription(answerDescription);
            } catch (e) {
                if (e instanceof DOMException && e.name === "InvalidStateError") {
                    console.error(e);
                    return;
                } else {
                    throw e;
                }
            }
            this.notifyPeer(notification.fromPeerId, "rtc_signal_description", pc.localDescription);
        }
    },
};

export class PeerToPeer {
    constructor(options) {
        this.options = options;
        this._currentPeerId = this.options.currentPeerId;
        if (debugShowLog) {
            console.log(
                `%c currentPeerId:${this._currentPeerId}`,
                "background: blue; color: white;"
            );
        }

        // peerId -> PeerInfos
        this.peersInfos = {};
        this._lastRequestId = -1;
        this._pendingRequestResolver = {};
        this._stopped = false;
    }

    stop() {
        this.closeAllConnections();
        this._stopped = true;
    }

    getConnectedPeerIds() {
        return Object.entries(this.peersInfos)
            .filter(
                ([id, infos]) =>
                    infos.peerConnection &&
                    infos.peerConnection.iceConnectionState === "connected" &&
                    infos.dataChannel &&
                    infos.dataChannel.readyState === "open"
            )
            .map(([id]) => id);
    }

    removePeer(peerId) {
        if (debugShowLog) {
            console.log(`%c REMOVE PEER ${peerId}`, "background: chocolate;");
        }
        this.notifySelf("ptp_remove", peerId);
        const peerInfos = this.peersInfos[peerId];
        if (!peerInfos) {
            return;
        }
        clearTimeout(peerInfos.fallbackTimeout);
        clearTimeout(peerInfos.zombieTimeout);
        peerInfos.dataChannel && peerInfos.dataChannel.close();
        peerInfos.peerConnection && peerInfos.peerConnection.close();
        delete this.peersInfos[peerId];
    }

    closeAllConnections() {
        for (const peerId of Object.keys(this.peersInfos)) {
            this.notifyAllPeers("ptp_disconnect");
            this.removePeer(peerId);
        }
    }

    async notifyAllPeers(notificationName, notificationPayload, { transport = "server" } = {}) {
        if (this._stopped) {
            return;
        }
        const transportPayload = {
            fromPeerId: this._currentPeerId,
            notificationName,
            notificationPayload,
        };
        if (transport === "server") {
            await this.options.broadcastAll(transportPayload);
        } else if (transport === "rtc") {
            for (const cliendId of Object.keys(this.peersInfos)) {
                this._channelNotify(cliendId, transportPayload);
            }
        } else {
            throw new Error(
                `Transport "${transport}" is not supported. Use "server" or "rtc" transport.`
            );
        }
    }

    notifyPeer(peerId, notificationName, notificationPayload, { transport = "server" } = {}) {
        if (this._stopped) {
            return;
        }
        if (debugShowNotifications) {
            if (notificationName === "ptp_request_result") {
                console.log(
                    `%c${Date.now()} - REQUEST RESULT SEND: %c${transport}:${
                        notificationPayload.requestId
                    }:${this._currentPeerId.slice("-5")}:${peerId.slice("-5")}`,
                    "color: #aaa;font-weight:bold;",
                    "color: #aaa;font-weight:normal"
                );
            } else if (notificationName === "ptp_request") {
                console.log(
                    `%c${Date.now()} - REQUEST SEND: %c${transport}:${
                        notificationPayload.requestName
                    }|${notificationPayload.requestId}:${this._currentPeerId.slice(
                        "-5"
                    )}:${peerId.slice("-5")}`,
                    "color: #aaa;font-weight:bold;",
                    "color: #aaa;font-weight:normal"
                );
            } else {
                console.log(
                    `%c${Date.now()} - NOTIFICATION SEND: %c${transport}:${notificationName}:${this._currentPeerId.slice(
                        "-5"
                    )}:${peerId.slice("-5")}`,
                    "color: #aaa;font-weight:bold;",
                    "color: #aaa;font-weight:normal"
                );
            }
        }
        const transportPayload = {
            fromPeerId: this._currentPeerId,
            toPeerId: peerId,
            notificationName,
            notificationPayload,
        };
        if (transport === "server") {
            this.options.broadcastAll(transportPayload);
        } else if (transport === "rtc") {
            this._channelNotify(peerId, transportPayload);
        } else {
            throw new Error(
                `Transport "${transport}" is not supported. Use "server" or "rtc" transport.`
            );
        }
    }

    notifySelf(notificationName, notificationPayload) {
        if (this._stopped) {
            return;
        }
        return this.handleNotification({ notificationName, notificationPayload });
    }

    handleNotification(notification) {
        if (this._stopped) {
            return;
        }
        const isInternalNotification =
            typeof notification.fromPeerId === "undefined" &&
            typeof notification.toPeerId === "undefined";
        if (
            isInternalNotification ||
            (notification.fromPeerId !== this._currentPeerId && !notification.toPeerId) ||
            notification.toPeerId === this._currentPeerId
        ) {
            if (debugShowNotifications) {
                if (notification.notificationName === "ptp_request_result") {
                    console.log(
                        `%c${Date.now()} - REQUEST RESULT RECEIVE: %c${
                            notification.notificationPayload.requestId
                        }:${notification.fromPeerId.slice("-5")}:${notification.toPeerId.slice(
                            "-5"
                        )}`,
                        "color: #aaa;font-weight:bold;",
                        "color: #aaa;font-weight:normal"
                    );
                } else if (notification.notificationName === "ptp_request") {
                    console.log(
                        `%c${Date.now()} - REQUEST RECEIVE: %c${
                            notification.notificationPayload.requestName
                        }|${
                            notification.notificationPayload.requestId
                        }:${notification.fromPeerId.slice("-5")}:${notification.toPeerId.slice(
                            "-5"
                        )}`,
                        "color: #aaa;font-weight:bold;",
                        "color: #aaa;font-weight:normal"
                    );
                } else {
                    console.log(
                        `%c${Date.now()} - NOTIFICATION RECEIVE: %c${
                            notification.notificationName
                        }:${notification.fromPeerId}:${notification.toPeerId}`,
                        "color: #aaa;font-weight:bold;",
                        "color: #aaa;font-weight:normal"
                    );
                }
            }
            try {
                const baseMethod = baseNotificationMethods[notification.notificationName];
                if (baseMethod) {
                    return baseMethod.call(this, notification);
                }
                if (this.options.onNotification) {
                    return this.options.onNotification(notification);
                }
            } catch (error) {
                console.groupCollapsed("=== ERROR: On notification in collaboration ===");
                console.error(error);
                console.groupEnd();
            }
        }
    }

    requestPeer(peerId, requestName, requestPayload, { transport = "server" } = {}) {
        if (this._stopped) {
            return;
        }
        return new Promise((resolve, reject) => {
            const requestId = this._getRequestId();

            const abort = (reason) => {
                clearTimeout(rejectTimeout);
                delete this._pendingRequestResolver[requestId];
                reject(new RequestError(reason || "Request was aborted."));
            };
            const rejectTimeout = setTimeout(
                () => abort("Request took too long (more than 10 seconds)."),
                10000
            );

            this._pendingRequestResolver[requestId] = {
                resolve,
                rejectTimeout,
                abort,
            };

            this.notifyPeer(
                peerId,
                "ptp_request",
                {
                    requestId,
                    requestName,
                    requestPayload,
                    requestTransport: transport,
                },
                { transport }
            );
        });
    }
    abortCurrentRequests() {
        for (const { abort } of Object.values(this._pendingRequestResolver)) {
            abort();
        }
    }
    _createPeer(peerId, { makeOffer = true } = {}) {
        if (this._stopped) {
            return;
        }
        if (debugShowLog) {
            console.log("CREATE CONNECTION with peer id:", peerId);
        }
        this.peersInfos[peerId] = {
            makingOffer: false,
            iceCandidateBuffer: [],
            backoffFactor: 0,
        };

        if (!navigator.onLine) {
            return this.peersInfos[peerId];
        }
        const pc = new RTCPeerConnection(this.options.peerConnectionConfig);

        if (makeOffer) {
            pc.onnegotiationneeded = async () => {
                if (debugShowLog) {
                    console.log(
                        `%c NEGONATION NEEDED: ${pc.connectionState}`,
                        "background: deeppink;"
                    );
                }
                try {
                    this.peersInfos[peerId].makingOffer = true;
                    if (debugShowLog) {
                        console.log(
                            `%ccreating and sending an offer`,
                            "background: darkmagenta; color: white;"
                        );
                    }
                    const offer = await pc.createOffer();
                    // Avoid race condition.
                    if (pc.signalingState !== "stable") {
                        return;
                    }
                    await pc.setLocalDescription(offer);
                    this.notifyPeer(peerId, "rtc_signal_description", pc.localDescription);
                } catch (err) {
                    console.error(err);
                } finally {
                    this.peersInfos[peerId].makingOffer = false;
                }
            };
        }
        pc.onicecandidate = async (event) => {
            if (event.candidate) {
                this.notifyPeer(peerId, "rtc_signal_icecandidate", event.candidate);
            }
        };
        pc.oniceconnectionstatechange = async () => {
            if (debugShowLog) {
                console.log("ICE STATE UPDATE: " + pc.iceConnectionState);
            }

            switch (pc.iceConnectionState) {
                case "failed":
                case "closed":
                    this.removePeer(peerId);
                    break;
                case "disconnected":
                    if (navigator.onLine) {
                        await this._recoverConnection(peerId, {
                            delay: 3000,
                            reason: "ice connection disconnected",
                        });
                    }
                    break;
                case "connected":
                    this.peersInfos[peerId].backoffFactor = 0;
                    break;
            }
        };
        // This event does not work in FF. Let's try with oniceconnectionstatechange if it is sufficient.
        pc.onconnectionstatechange = async () => {
            if (debugShowLog) {
                console.log("CONNECTION STATE UPDATE:" + pc.connectionState);
            }

            switch (pc.connectionState) {
                case "failed":
                case "closed":
                    this.removePeer(peerId);
                    break;
                case "disconnected":
                    if (navigator.onLine) {
                        await this._recoverConnection(peerId, {
                            delay: 3000,
                            reason: "connection disconnected",
                        });
                    }
                    break;
                case "connected":
                case "completed":
                    this.peersInfos[peerId].backoffFactor = 0;
                    break;
            }
        };
        pc.onicecandidateerror = async (error) => {
            if (debugShowLog) {
                console.groupCollapsed("=== ERROR: onIceCandidate ===");
                console.log(
                    "connectionState: " +
                        pc.connectionState +
                        " - iceState: " +
                        pc.iceConnectionState
                );
                console.trace(error);
                console.groupEnd();
            }
            this._recoverConnection(peerId, { delay: 3000, reason: "ice candidate error" });
        };
        const dataChannel = pc.createDataChannel("notifications", { negotiated: true, id: 1 });
        let message = [];
        dataChannel.onmessage = (event) => {
            if (event.data !== "-") {
                message.push(event.data);
            } else {
                this.handleNotification(JSON.parse(message.join("")));
                message = [];
            }
        };
        dataChannel.onopen = (event) => {
            this.notifySelf("rtc_data_channel_open", {
                connectionPeerId: peerId,
            });
        };

        this.peersInfos[peerId].peerConnection = pc;
        this.peersInfos[peerId].dataChannel = dataChannel;

        return this.peersInfos[peerId];
    }
    async _addIceCandidate(peerInfos, candidate) {
        const rtcIceCandidate = new RTCIceCandidate(candidate);
        try {
            await peerInfos.peerConnection.addIceCandidate(rtcIceCandidate);
        } catch (error) {
            // Ignored.
            console.groupCollapsed("=== ERROR: ADD ICE CANDIDATE ===");
            console.trace(error);
            console.groupEnd();
        }
    }

    _channelNotify(peerId, transportPayload) {
        if (this._stopped) {
            return;
        }
        const peerInfo = this.peersInfos[peerId];
        const dataChannel = peerInfo && peerInfo.dataChannel;

        if (!dataChannel || dataChannel.readyState !== "open") {
            if (peerInfo && !peerInfo.zombieTimeout) {
                if (debugShowLog) {
                    console.warn(
                        `Impossible to communicate with peer ${peerId}. The connection will be killed in 10 seconds if the datachannel state has not changed.`
                    );
                }
                this._killPotentialZombie(peerId);
            }
        } else {
            const str = JSON.stringify(transportPayload);
            const size = str.length;
            const maxStringLength = 5000;
            let from = 0;
            let to = maxStringLength;
            while (from < size) {
                dataChannel.send(str.slice(from, to));
                from = to;
                to = to += maxStringLength;
            }
            dataChannel.send("-");
        }
    }

    _getRequestId() {
        this._lastRequestId++;
        return this._lastRequestId;
    }

    async _onRequest(fromPeerId, requestId, requestName, requestPayload, requestTransport) {
        if (this._stopped) {
            return;
        }
        const requestFunction = this.options.onRequest && this.options.onRequest[requestName];
        const result = await requestFunction({
            fromPeerId,
            requestId,
            requestName,
            requestPayload,
        });
        this.notifyPeer(
            fromPeerId,
            "ptp_request_result",
            { requestId, result },
            { transport: requestTransport }
        );
    }
    /**
     * Attempts a connection recovery by updating the tracks, which will start
     * a new transaction: negotiationneeded -> offer -> answer -> ...
     *
     * @private
     * @param {Object} [param1]
     * @param {number} [param1.delay] in ms
     * @param {string} [param1.reason]
     */
    _recoverConnection(peerId, { delay = 0, reason = "" } = {}) {
        if (this._stopped) {
            this.removePeer(peerId);
            return;
        }
        const peerInfos = this.peersInfos[peerId];
        if (!peerInfos || peerInfos.fallbackTimeout) {
            return;
        }
        const backoffFactor = this.peersInfos[peerId].backoffFactor;
        const backoffDelay = delay * Math.pow(2, backoffFactor);
        // Stop trying to recover the connection after 10 attempts.
        if (backoffFactor > 10) {
            if (debugShowLog) {
                console.log(
                    `%c STOP RTC RECOVERY: impossible to connect to peer ${peerId}: ${reason}`,
                    "background: darkred; color: white;"
                );
            }
            return;
        }

        peerInfos.fallbackTimeout = setTimeout(async () => {
            peerInfos.fallbackTimeout = undefined;
            const pc = peerInfos.peerConnection;
            if (!pc || pc.iceConnectionState === "connected") {
                return;
            }
            if (["connected", "closed"].includes(pc.connectionState)) {
                return;
            }
            // hard reset: recreating a RTCPeerConnection
            if (debugShowLog) {
                console.log(
                    `%c RTC RECOVERY: calling back peer ${peerId} to salvage the connection ${pc.iceConnectionState} after ${backoffDelay}ms, reason: ${reason}`,
                    "background: darkorange; color: white;"
                );
            }
            this.removePeer(peerId);
            const newPeerInfos = this._createPeer(peerId);
            newPeerInfos.backoffFactor = backoffFactor + 1;
        }, backoffDelay);
    }
    // todo: do we try to salvage the connection after killing the zombie ?
    // Maybe the salvage should be done when the connection is dropped.
    _killPotentialZombie(peerId) {
        if (this._stopped) {
            this.removePeer(peerId);
            return;
        }
        const peerInfos = this.peersInfos[peerId];
        if (!peerInfos || peerInfos.zombieTimeout) {
            return;
        }

        // If there is no connection after 10 seconds, terminate.
        peerInfos.zombieTimeout = setTimeout(() => {
            if (peerInfos && peerInfos.dataChannel && peerInfos.dataChannel.readyState !== "open") {
                if (debugShowLog) {
                    console.log(`%c KILL ZOMBIE ${peerId}`, "background: red;");
                }
                this.removePeer(peerId);
            } else {
                if (debugShowLog) {
                    console.log(`%c NOT A ZOMBIE ${peerId}`, "background: green;");
                }
            }
        }, 10000);
    }
}

export class RequestError extends Error {
    constructor(message) {
        super(message);
        this.name = "RequestError";
    }
}
