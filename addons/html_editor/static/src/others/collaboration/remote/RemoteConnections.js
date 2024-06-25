import { RemotePeerToPeer } from "./RemotePeerToPeer";
import { RemoteSFU } from "./RemoteSFU";
import { debugLog, RequestError } from "./remoteHelpers";

export class RemoteConnections {
    constructor(config) {
        this.config = config;
        this.pendingRequestResolver = {};
        this.lastRequestId = 0;
        this.stopped = false;
    }
    async start() {
        if (this.config.sfuConfig) {
            this.remoteInterface = new RemoteSFU(this.config);
            this.remoteInterface.addEventListener("sfu-connected", () => {
                this.notifyAllPeers("remote_ping", this.config.getRemotePingPayload());
            });
            await this.remoteInterface.start();
        } else if (this.config.peerToPeerConfig) {
            this.remoteInterface = new RemotePeerToPeer(this.config);
            this.remoteInterface.addEventListener("ptp-ping", ({ detail: toPeerId }) => {
                this.notifyPeer(toPeerId, "remote_ping", this.config.getRemotePingPayload());
            });
            await this.remoteInterface.start();
        } else {
            throw new Error("Invalid params. Must provide either sfuConfig or peerToPeerConfig.");
        }
        this.remoteInterface.addEventListener(
            "remote-notification",
            ({ detail: { notificationName, fromPeerId, notificationPayload } }) =>
                this.handleNotification(notificationName, fromPeerId, notificationPayload)
        );
    }
    stop() {
        this.stopped = true;
        this.abortCurrentRequests();
        this.remoteInterface.stop();
    }

    notifyAllPeers(notificationName, notificationPayload) {
        debugLog(`⇧⇧⇧`, notificationName, notificationPayload);
        if (notificationName in baseNotificationMethods) {
            throw new Error(`Notification name ${notificationName} is reserved.`);
        }
        this.remoteInterface.notifyAllPeers(notificationName, notificationPayload);
    }
    notifyPeer(toPeerId, notificationName, notificationPayload, { _isInternal } = {}) {
        debugLog(` ⇧ `, notificationName, this.config.peerId, toPeerId, notificationPayload);
        if (!_isInternal && notificationName in baseNotificationMethods) {
            throw new Error(`Notification name ${notificationName} is reserved.`);
        }
        this.remoteInterface.notifyPeer(toPeerId, notificationName, notificationPayload);
    }
    handleNotification(notificationName, fromPeerId, notificationPayload) {
        debugLog(` ⇩ `, notificationName, fromPeerId, this.config.peerId, notificationPayload);
        if (notificationName in baseNotificationMethods) {
            baseNotificationMethods[notificationName](this, {
                fromPeerId,
                notificationName,
                notificationPayload,
            });
        } else {
            this.config.handleNotification(notificationName, fromPeerId, notificationPayload);
        }
    }

    requestPeer(peerId, requestName, requestPayload) {
        if (this.stopped) {
            return;
        }
        return new Promise((resolve, reject) => {
            const requestId = this.getRequestId();

            const abort = (reason) => {
                clearTimeout(rejectTimeout);
                delete this.pendingRequestResolver[requestId];
                reject(new RequestError(reason || "Request was aboted."));
            };
            const rejectTimeout = setTimeout(
                () => abort(`Request "${requestName}" took too long (more than 10 seconds).`),
                10000
            );

            this.pendingRequestResolver[requestId] = {
                resolve,
                rejectTimeout,
                abort,
            };

            this.notifyPeer(
                peerId,
                "__REQUEST__",
                {
                    requestId,
                    requestName,
                    requestPayload,
                },
                { _isInternal: true }
            );
        });
    }
    abortCurrentRequests() {
        for (const { abort } of Object.values(this.pendingRequestResolver)) {
            abort();
        }
    }
    getRequestId() {
        this.lastRequestId++;
        return this.lastRequestId;
    }
    async onRequest(fromPeerId, requestId, requestName, requestPayload) {
        if (this.stopped) {
            return;
        }
        const result = await this.config.handleRequest(requestName, fromPeerId, {
            fromPeerId,
            requestId,
            requestName,
            requestPayload,
        });
        this.notifyPeer(
            fromPeerId,
            "__REQUEST_RESULT__",
            { requestId, result },
            { _isInternal: true }
        );
    }
}

const baseNotificationMethods = {
    __REQUEST__: async function (remoteConnection, notification) {
        const { requestId, requestName, requestPayload } = notification.notificationPayload;
        remoteConnection.onRequest(notification.fromPeerId, requestId, requestName, requestPayload);
    },
    __REQUEST_RESULT__: function (remoteConnection, notification) {
        const { requestId, result } = notification.notificationPayload;
        // If not in pendingRequestResolver, it means it has timeout.
        if (remoteConnection.pendingRequestResolver[requestId]) {
            clearTimeout(remoteConnection.pendingRequestResolver[requestId].rejectTimeout);
            remoteConnection.pendingRequestResolver[requestId].resolve(result);
            delete remoteConnection.pendingRequestResolver[requestId];
        }
    },
};
