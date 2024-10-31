/** @odoo-module */
import { browser } from "@web/core/browser/browser";
const localStorage = browser.localStorage;

const urlParams = new URLSearchParams(window.location.search);
const collaborationDebug = urlParams.get('collaborationDebug');
const COLLABORATION_LOCALSTORAGE_KEY = 'odoo_editor_collaboration_debug';
if (typeof collaborationDebug === 'string') {
    if (collaborationDebug === 'false') {
        localStorage.removeItem(
            COLLABORATION_LOCALSTORAGE_KEY,
            urlParams.get('collaborationDebug'),
        );
    } else {
        localStorage.setItem(COLLABORATION_LOCALSTORAGE_KEY, urlParams.get('collaborationDebug'));
    }
}
const debugValue = localStorage.getItem(COLLABORATION_LOCALSTORAGE_KEY);

const debugShowLog = ['', 'true', 'all'].includes(debugValue);
const debugShowNotifications = debugValue === 'all';

const baseNotificationMethods = {
    ptp_request: async function(notification) {
        const { requestId, requestName, requestPayload, requestTransport } =
            notification.notificationPayload;
        this._onRequest(
            notification.fromClientId,
            requestId,
            requestName,
            requestPayload,
            requestTransport,
        );
    },
    ptp_request_result: function(notification) {
        const { requestId, result } = notification.notificationPayload;
        // If not in _pendingRequestResolver, it means it has timeout.
        if (this._pendingRequestResolver[requestId]) {
            clearTimeout(this._pendingRequestResolver[requestId].rejectTimeout);
            this._pendingRequestResolver[requestId].resolve(result);
            delete this._pendingRequestResolver[requestId];
        }
    },

    ptp_join: async function (notification) {
        const clientId = notification.fromClientId;
        if (this.clientsInfos[clientId] && this.clientsInfos[clientId].peerConnection) {
            return this.clientsInfos[clientId];
        }
        this._createClient(clientId);
    },

    rtc_signal_icecandidate: async function (notification) {
        if (debugShowLog) console.log(`%creceive candidate`, 'background: darkgreen; color: white;');
        const clientInfos = this.clientsInfos[notification.fromClientId];
        if (
            !clientInfos ||
            !clientInfos.peerConnection ||
            clientInfos.peerConnection.connectionState === 'closed'
        ) {
            console.groupCollapsed('=== ERROR: Handle Ice Candidate from undefined|closed ===');
            console.trace(clientInfos);
            console.groupEnd();
            return;
        }
        if (!clientInfos.peerConnection.remoteDescription) {
            clientInfos.iceCandidateBuffer.push(notification.notificationPayload);
        } else {
            this._addIceCandidate(clientInfos, notification.notificationPayload);
        }
    },
    rtc_signal_description: async function (notification) {
        const description = notification.notificationPayload;
        if (debugShowLog)
            console.log(
                `%cdescription received:`,
                'background: blueviolet; color: white;',
                description,
            );

        const clientInfos =
            this.clientsInfos[notification.fromClientId] ||
            this._createClient(notification.fromClientId);
        const pc = clientInfos.peerConnection;

        if (!pc || pc.connectionState === 'closed') {
            if (debugShowLog) {
                console.groupCollapsed('=== ERROR: handle offer ===');
                console.log(
                    'An offer has been received for a non-existent peer connection - client: ' +
                        notification.fromClientId,
                );
                console.trace(pc && pc.connectionState);
                console.groupEnd();
            }
            return;
        }

        // Skip if we already have an offer.
        if (pc.signalingState === 'have-remote-offer') {
            return;
        }

        // If there is a racing conditing with the signaling offer (two
        // being sent at the same time). We need one client that abort by
        // rollbacking to a stable signaling state where the other is
        // continuing the process. The client that is polite is the one that
        // will rollback.
        const isPolite =
            ('' + notification.fromClientId).localeCompare('' + this._currentClientId) === 1;
        if (debugShowLog)
            console.log(
                `%cisPolite: %c${isPolite}`,
                'background: deepskyblue;',
                `background:${isPolite ? 'green' : 'red'}`,
            );

        const isOfferRacing =
            description.type === 'offer' &&
            (clientInfos.makingOffer || pc.signalingState !== 'stable');
        // If there is a racing conditing with the signaling offer and the
        // client is impolite, we must not process this offer and wait for
        // the answer for the signaling process to continue.
        if (isOfferRacing && !isPolite) {
            if (debugShowLog)
                console.log(
                    `%creturn because isOfferRacing && !isPolite. pc.signalingState: ${pc.signalingState}`,
                    'background: red;',
                );
            return;
        }
        if (debugShowLog) console.log(`%cisOfferRacing: ${isOfferRacing}`, 'background: red;');

        try {
            if (isOfferRacing) {
                if (debugShowLog)
                    console.log(`%c SETREMOTEDESCRIPTION 1`, 'background: navy; color:white;');
                await Promise.all([
                    pc.setLocalDescription({ type: 'rollback' }),
                    pc.setRemoteDescription(description),
                ]);
            } else {
                if (debugShowLog)
                    console.log(`%c SETREMOTEDESCRIPTION 2`, 'background: navy; color:white;');
                await pc.setRemoteDescription(description);
            }
        } catch (e) {
            if (e instanceof DOMException && e.name === 'InvalidStateError') {
                console.error(e);
                return;
            } else {
                throw e;
            }
        }
        if (clientInfos.iceCandidateBuffer.length) {
            for (const candidate of clientInfos.iceCandidateBuffer) {
                await this._addIceCandidate(clientInfos, candidate);
            }
            clientInfos.iceCandidateBuffer.splice(0);
        }
        if (description.type === 'offer') {
            const answerDescription = await pc.createAnswer();
            try {
                await pc.setLocalDescription(answerDescription);
            } catch (e) {
                if (e instanceof DOMException && e.name === 'InvalidStateError') {
                    console.error(e);
                    return;
                } else {
                    throw e;
                }
            }
            this.notifyClient(
                notification.fromClientId,
                'rtc_signal_description',
                pc.localDescription,
            );
        }
    },
};

export class PeerToPeer {
    constructor(options) {
        this.options = options;
        this._currentClientId = this.options.currentClientId;
        if (debugShowLog)
            console.log(
                `%c currentClientId:${this._currentClientId}`,
                'background: blue; color: white;',
            );

        // clientId -> ClientInfos
        this.clientsInfos = {};
        this._lastRequestId = -1;
        this._pendingRequestResolver = {};
        this._stopped = false;
    }

    stop() {
        this.closeAllConnections();
        this._stopped = true;
    }

    getConnectedClientIds() {
        return Object.entries(this.clientsInfos)
            .filter(
                ([id, infos]) =>
                    infos.peerConnection && infos.peerConnection.iceConnectionState === 'connected' &&
                    infos.dataChannel && infos.dataChannel.readyState === 'open',
            )
            .map(([id]) => id);
    }

    removeClient(clientId) {
        if (debugShowLog) console.log(`%c REMOVE CLIENT ${clientId}`, 'background: chocolate;');
        this.notifySelf('ptp_remove', clientId);
        const clientInfos = this.clientsInfos[clientId];
        if (!clientInfos) return;
        clearTimeout(clientInfos.fallbackTimeout);
        clearTimeout(clientInfos.zombieTimeout);
        clientInfos.dataChannel && clientInfos.dataChannel.close();
        clientInfos.peerConnection && clientInfos.peerConnection.close();
        delete this.clientsInfos[clientId];
    }

    closeAllConnections() {
        for (const clientId of Object.keys(this.clientsInfos)) {
            this.notifyAllClients('ptp_disconnect');
            this.removeClient(clientId);
        }
    }

    async notifyAllClients(notificationName, notificationPayload, { transport = 'server' } = {}) {
        if (this._stopped) {
            return;
        }
        const transportPayload = {
            fromClientId: this._currentClientId,
            notificationName,
            notificationPayload,
        };
        if (transport === 'server') {
            await this.options.broadcastAll(transportPayload);
        } else if (transport === 'rtc') {
            for (const cliendId of Object.keys(this.clientsInfos)) {
                this._channelNotify(cliendId, transportPayload);
            }
        } else {
            throw new Error(
                `Transport "${transport}" is not supported. Use "server" or "rtc" transport.`,
            );
        }
    }

    notifyClient(clientId, notificationName, notificationPayload, { transport = 'server' } = {}) {
        if (this._stopped) {
            return;
        }
        if (debugShowNotifications) {
            if (notificationName === 'ptp_request_result') {
                console.log(
                    `%c${Date.now()} - REQUEST RESULT SEND: %c${transport}:${
                        notificationPayload.requestId
                    }:${this._currentClientId.slice('-5')}:${clientId.slice('-5')}`,
                    'color: #aaa;font-weight:bold;',
                    'color: #aaa;font-weight:normal',
                );
            } else if (notificationName === 'ptp_request') {
                console.log(
                    `%c${Date.now()} - REQUEST SEND: %c${transport}:${
                        notificationPayload.requestName
                    }|${notificationPayload.requestId}:${this._currentClientId.slice(
                        '-5',
                    )}:${clientId.slice('-5')}`,
                    'color: #aaa;font-weight:bold;',
                    'color: #aaa;font-weight:normal',
                );
            } else {
                console.log(
                    `%c${Date.now()} - NOTIFICATION SEND: %c${transport}:${notificationName}:${this._currentClientId.slice(
                        '-5',
                    )}:${clientId.slice('-5')}`,
                    'color: #aaa;font-weight:bold;',
                    'color: #aaa;font-weight:normal',
                );
            }
        }
        const transportPayload = {
            fromClientId: this._currentClientId,
            toClientId: clientId,
            notificationName,
            notificationPayload,
        };
        if (transport === 'server') {
            this.options.broadcastAll(transportPayload);
        } else if (transport === 'rtc') {
            this._channelNotify(clientId, transportPayload);
        } else {
            throw new Error(
                `Transport "${transport}" is not supported. Use "server" or "rtc" transport.`,
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
            typeof notification.fromClientId === 'undefined' &&
            typeof notification.toClientId === 'undefined';
        if (
            isInternalNotification ||
            (notification.fromClientId !== this._currentClientId && !notification.toClientId) ||
            notification.toClientId === this._currentClientId
        ) {
            if (debugShowNotifications) {
                if (notification.notificationName === 'ptp_request_result') {
                    console.log(
                        `%c${Date.now()} - REQUEST RESULT RECEIVE: %c${
                            notification.notificationPayload.requestId
                        }:${notification.fromClientId.slice('-5')}:${notification.toClientId.slice(
                            '-5',
                        )}`,
                        'color: #aaa;font-weight:bold;',
                        'color: #aaa;font-weight:normal',
                    );
                } else if (notification.notificationName === 'ptp_request') {
                    console.log(
                        `%c${Date.now()} - REQUEST RECEIVE: %c${
                            notification.notificationPayload.requestName
                        }|${
                            notification.notificationPayload.requestId
                        }:${notification.fromClientId.slice('-5')}:${notification.toClientId.slice(
                            '-5',
                        )}`,
                        'color: #aaa;font-weight:bold;',
                        'color: #aaa;font-weight:normal',
                    );
                } else {
                    console.log(
                        `%c${Date.now()} - NOTIFICATION RECEIVE: %c${
                            notification.notificationName
                        }:${notification.fromClientId}:${notification.toClientId}`,
                        'color: #aaa;font-weight:bold;',
                        'color: #aaa;font-weight:normal',
                    );
                }
            }
            const baseMethod = baseNotificationMethods[notification.notificationName];
            if (baseMethod) {
                return baseMethod.call(this, notification);
            }
            if (this.options.onNotification) {
                return this.options.onNotification(notification);
            }
        }
    }

    requestClient(clientId, requestName, requestPayload, { transport = 'server' } = {}) {
        if (this._stopped) {
            return;
        }
        return new Promise((resolve, reject) => {
            const requestId = this._getRequestId();

            const abort = (reason) => {
                clearTimeout(rejectTimeout);
                delete this._pendingRequestResolver[requestId];
                reject(new RequestError(reason || 'Request was aborted.'));
            };
            const rejectTimeout = setTimeout(
                () => abort('Request took too long (more than 10 seconds).'),
                10000
            );

            this._pendingRequestResolver[requestId] = {
                resolve,
                rejectTimeout,
                abort,
            };

            this.notifyClient(
                clientId,
                'ptp_request',
                {
                    requestId,
                    requestName,
                    requestPayload,
                    requestTransport: transport,
                },
                { transport },
            );
        });
    }
    abortCurrentRequests() {
        for (const { abort } of Object.values(this._pendingRequestResolver)) {
            abort();
        }
    }
    _createClient(clientId, { makeOffer = true } = {}) {
        if (this._stopped) {
            return;
        }
        if (debugShowLog) console.log('CREATE CONNECTION with client id:', clientId);
        this.clientsInfos[clientId] = {
            makingOffer: false,
            iceCandidateBuffer: [],
            backoffFactor: 0,
        };

        if (!navigator.onLine) {
            return this.clientsInfos[clientId];
        }
        const pc = new RTCPeerConnection(this.options.peerConnectionConfig);

        if (makeOffer) {
            pc.onnegotiationneeded = async () => {
                if (debugShowLog)
                    console.log(
                        `%c NEGONATION NEEDED: ${pc.connectionState}`,
                        'background: deeppink;',
                    );
                try {
                    this.clientsInfos[clientId].makingOffer = true;
                    if (debugShowLog)
                        console.log(
                            `%ccreating and sending an offer`,
                            'background: darkmagenta; color: white;',
                        );
                    const offer = await pc.createOffer();
                    // Avoid race condition.
                    if (pc.signalingState !== 'stable') {
                        return;
                    }
                    await pc.setLocalDescription(offer);
                    this.notifyClient(clientId, 'rtc_signal_description', pc.localDescription);
                } catch (err) {
                    console.error(err);
                } finally {
                    this.clientsInfos[clientId].makingOffer = false;
                }
            };
        }
        pc.onicecandidate = async event => {
            if (event.candidate) {
                this.notifyClient(clientId, 'rtc_signal_icecandidate', event.candidate);
            }
        };
        pc.oniceconnectionstatechange = async () => {
            if (debugShowLog) console.log('ICE STATE UPDATE: ' + pc.iceConnectionState);

            switch (pc.iceConnectionState) {
                case 'failed':
                case 'closed':
                    this.removeClient(clientId);
                    break;
                case 'disconnected':
                    if (navigator.onLine) {
                        await this._recoverConnection(clientId, {
                            delay: 3000,
                            reason: 'ice connection disconnected',
                        });
                    }
                    break;
                case 'connected':
                    this.clientsInfos[clientId].backoffFactor = 0;
                    break;
            }
        };
        // This event does not work in FF. Let's try with oniceconnectionstatechange if it is sufficient.
        pc.onconnectionstatechange = async () => {
            if (debugShowLog) console.log('CONNECTION STATE UPDATE:' + pc.connectionState);

            switch (pc.connectionState) {
                case 'failed':
                case 'closed':
                    this.removeClient(clientId);
                    break;
                case 'disconnected':
                    if (navigator.onLine) {
                        await this._recoverConnection(clientId, {
                            delay: 3000,
                            reason: 'connection disconnected',
                        });
                    }
                    break;
                case 'connected':
                case 'completed':
                    this.clientsInfos[clientId].backoffFactor = 0;
                    break;
            }
        };
        pc.onicecandidateerror = async error => {
            if (debugShowLog) {
                console.groupCollapsed('=== ERROR: onIceCandidate ===');
                console.log(
                    'connectionState: ' +
                        pc.connectionState +
                        ' - iceState: ' +
                        pc.iceConnectionState,
                );
                console.trace(error);
                console.groupEnd();
            }
            this._recoverConnection(clientId, { delay: 3000, reason: 'ice candidate error' });
        };
        const dataChannel = pc.createDataChannel('notifications', { negotiated: true, id: 1 });
        let message = [];
        dataChannel.onmessage = event => {
            if (event.data !== '-') {
                message.push(event.data);
            } else {
                this.handleNotification(JSON.parse(message.join('')));
                message = [];
            }
        };
        dataChannel.onopen = event => {
            this.notifySelf('rtc_data_channel_open', {
                connectionClientId: clientId,
            });
        };

        this.clientsInfos[clientId].peerConnection = pc;
        this.clientsInfos[clientId].dataChannel = dataChannel;

        return this.clientsInfos[clientId];
    }
    async _addIceCandidate(clientInfos, candidate) {
        const rtcIceCandidate = new RTCIceCandidate(candidate);
        try {
            await clientInfos.peerConnection.addIceCandidate(rtcIceCandidate);
        } catch (error) {
            // Ignored.
            console.groupCollapsed('=== ERROR: ADD ICE CANDIDATE ===');
            console.trace(error);
            console.groupEnd();
        }
    }

    _channelNotify(clientId, transportPayload) {
        if (this._stopped) {
            return;
        }
        const clientInfo = this.clientsInfos[clientId];
        const dataChannel = clientInfo && clientInfo.dataChannel;

        if (!dataChannel || dataChannel.readyState !== 'open') {
            if (clientInfo && !clientInfo.zombieTimeout) {
                if (debugShowLog) console.warn(
                    `Impossible to communicate with client ${clientId}. The connection will be killed in 10 seconds if the datachannel state has not changed.`,
                );
                this._killPotentialZombie(clientId);
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
            dataChannel.send('-');
        }
    }

    _getRequestId() {
        this._lastRequestId++;
        return this._lastRequestId;
    }

    async _onRequest(fromClientId, requestId, requestName, requestPayload, requestTransport) {
        if (this._stopped) {
            return;
        }
        const requestFunction = this.options.onRequest && this.options.onRequest[requestName];
        const result = await requestFunction({
            fromClientId,
            requestId,
            requestName,
            requestPayload,
        });
        this.notifyClient(
            fromClientId,
            'ptp_request_result',
            { requestId, result },
            { transport: requestTransport },
        );
    }
    /**
     * Attempts a connection recovery by updating the tracks, which will start a new transaction:
     * negotiationneeded -> offer -> answer -> ...
     *
     * @private
     * @param {Object} [param1]
     * @param {number} [param1.delay] in ms
     * @param {string} [param1.reason]
     */
    _recoverConnection(clientId, { delay = 0, reason = '' } = {}) {
        if (this._stopped) {
            this.removeClient(clientId);
            return;
        }
        const clientInfos = this.clientsInfos[clientId];
        if (!clientInfos || clientInfos.fallbackTimeout) return;
        const backoffFactor = this.clientsInfos[clientId].backoffFactor;
        const backoffDelay = delay * Math.pow(2, backoffFactor);
        // Stop trying to recover the connection after 10 attempts.
        if (backoffFactor > 10) {
            if (debugShowLog) {
                console.log(
                    `%c STOP RTC RECOVERY: impossible to connect to client ${clientId}: ${reason}`,
                    'background: darkred; color: white;',
                );
            }
            return;
        }

        clientInfos.fallbackTimeout = setTimeout(async () => {
            clientInfos.fallbackTimeout = undefined;
            const pc = clientInfos.peerConnection;
            if (!pc || pc.iceConnectionState === 'connected') {
                return;
            }
            if (['connected', 'closed'].includes(pc.connectionState)) {
                return;
            }
            // hard reset: recreating a RTCPeerConnection
            if (debugShowLog)
                console.log(
                    `%c RTC RECOVERY: calling back client ${clientId} to salvage the connection ${pc.iceConnectionState} after ${backoffDelay}ms, reason: ${reason}`,
                    'background: darkorange; color: white;',
                );
            this.removeClient(clientId);
            const newClientInfos = this._createClient(clientId);
            newClientInfos.backoffFactor = backoffFactor + 1;
        }, backoffDelay);
    }
    // todo: do we try to salvage the connection after killing the zombie ?
    // Maybe the salvage should be done when the connection is dropped.
    _killPotentialZombie(clientId) {
        if (this._stopped) {
            this.removeClient(clientId);
            return;
        }
        const clientInfos = this.clientsInfos[clientId];
        if (!clientInfos || clientInfos.zombieTimeout) {
            return;
        }

        // If there is no connection after 10 seconds, terminate.
        clientInfos.zombieTimeout = setTimeout(() => {
            if (clientInfos && clientInfos.dataChannel && clientInfos.dataChannel.readyState !== 'open') {
                if (debugShowLog) console.log(`%c KILL ZOMBIE ${clientId}`, 'background: red;');
                this.removeClient(clientId);
            } else {
                if (debugShowLog) console.log(`%c NOT A ZOMBIE ${clientId}`, 'background: green;');
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
