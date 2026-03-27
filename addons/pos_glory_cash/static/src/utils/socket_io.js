// https://socket.io/docs/v4/engine-io-protocol/#protocol
const PACKET_TYPES = {
    OPEN: "0",
    CLOSE: "1",
    PING: "2",
    PONG: "3",
    MESSAGE: "4",
};

// https://socket.io/docs/v4/socket-io-protocol/#exchange-protocol
const MSG_TYPES = {
    CONNECT: "0",
    DISCONNECT: "1",
    EVENT: "2",
    ACK: "3",
    CONNECT_ERROR: "4",
    BINARY_EVENT: "5",
    BINARY_ACK: "6",
};

const CONNECTION_TIMEOUT_MS = 10000;
const RECONNECT_DELAY_MS = 5000;

export class SocketIoService {
    /**
     * @param {import("models").SocketIoCallbacks} callbacks
     */
    constructor(callbacks) {
        this.setup(...arguments);
    }

    /**
     * @param {import("models").SocketIoCallbacks} callbacks
     */
    setup(callbacks) {
        this.callbacks = callbacks;
        this._reset();

        // Chrome slows down our pings when the tab is inactive, causing the websocket
        // to disconnect. Instead of this, we disconnect it ourselves when the tab
        // loses focus, and reconnect once focus is restored.
        document.addEventListener("visibilitychange", () => {
            if (!this.websocket) {
                return;
            }
            if (document.visibilityState === "hidden") {
                this.websocket.close();
            } else if (document.visibilityState === "visible" && this.closed) {
                this.connect(this.currentUrl);
            }
        });
    }

    _reset() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.onclose = null;
            this.websocket.close();
        }
        this.websocket = null;
        this.currentUrl = null;
        this.socketId = null;

        if (this.pingIntervalId) {
            clearInterval(this.pingIntervalId);
        }
        this.pingIntervalId = null;
        if (this.reconnectTimeoutId) {
            clearInterval(this.reconnectTimeoutId);
        }
        this.reconnectTimeoutId = null;

        if (this.pongTimeoutIds) {
            for (const timeoutId of this.pongTimeoutIds) {
                clearTimeout(timeoutId);
            }
        }
        this.pongTimeoutIds = [];
    }

    /**
     * @param {string} url
     */
    connect(url) {
        if (this.websocket) {
            this._reset();
        }
        this.currentUrl = url;
        this.websocket = new WebSocket(this.currentUrl);

        this.websocket.onclose = () => {
            if (this.pingIntervalId) {
                clearInterval(this.pingIntervalId);
            }
            if (document.visibilityState === "visible") {
                this.callbacks.onClose();
                this.reconnectTimeoutId = setTimeout(
                    () => this.connect(this.currentUrl),
                    RECONNECT_DELAY_MS
                );
            }
        };
        this.websocket.onmessage = (event) => this._onMessageReceived(event.data);
    }

    sendMessage(message) {
        const messageArray = Array.isArray(message) ? message : [message];
        const jsonData = JSON.stringify(messageArray);
        const payload = `${MSG_TYPES.EVENT}${jsonData}`;
        this._sendPacket(PACKET_TYPES.MESSAGE, payload);
    }

    get closed() {
        return this.websocket?.readyState !== WebSocket.OPEN;
    }

    _sendPacket(packetType, data) {
        this.websocket.send(`${packetType}${data}`);
    }

    _handleOpenMessage(data) {
        const info = JSON.parse(data);
        this.socketId = info.sid;
        this.pingIntervalId = setInterval(() => {
            this.websocket.send(PACKET_TYPES.PING);
            const pongTimeoutId = setTimeout(() => {
                this.websocket.close();
            }, CONNECTION_TIMEOUT_MS);
            this.pongTimeoutIds.push(pongTimeoutId);
        }, info.pingInterval);
    }

    async _handleMessage(data) {
        const messageType = data[0];
        const messageBody = data.slice(1);
        switch (messageType) {
            case MSG_TYPES.CONNECT: {
                this.callbacks.onConnect();
                return;
            }
            case MSG_TYPES.EVENT: {
                const body = JSON.parse(messageBody);
                if (!Array.isArray(body) || body.length === 0) {
                    this.websocket.close();
                    return;
                }
                this.callbacks.onEvent(body);
                return;
            }
        }
    }

    _onMessageReceived(data) {
        if (data instanceof Blob) {
            this.callbacks.onBinaryEvent(data);
            return;
        }
        const packetType = data[0];
        const packetData = data.slice(1);
        if (packetType === PACKET_TYPES.OPEN) {
            this._handleOpenMessage(packetData);
        } else if (packetType === PACKET_TYPES.PONG) {
            for (const timeoutId of this.pongTimeoutIds) {
                clearTimeout(timeoutId);
            }
            this.pongTimeoutIds = [];
        } else if (packetType === PACKET_TYPES.MESSAGE) {
            this._handleMessage(packetData);
        }
    }
}
