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

export class SocketIoService {
    /**
     * @param {string} url
     * @param {import("models").SocketIoCallbacks} callbacks
     */
    constructor(url, callbacks) {
        this.setup(...arguments);
    }

    /**
     * @param {string} url
     * @param {import("models").SocketIoCallbacks} callbacks
     */
    setup(url, callbacks) {
        this.websocket = null;
        this.socketId = null;
        this.pingIntervalId = null;

        this.callbacks = callbacks;
        this._connect(url);
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

    _connect(url) {
        this.websocket = new WebSocket(url);
        this.websocket.onclose = () => {
            if (this.pingIntervalId) {
                clearInterval(this.pingIntervalId);
            }
            setTimeout(() => this._connect(url), 5000);
        };
        this.websocket.onmessage = (event) => this._onMessageReceived(event.data);
    }

    _sendPacket(packetType, data) {
        this.websocket.send(`${packetType}${data}`);
    }

    _handleOpenMessage(data) {
        const info = JSON.parse(data);
        this.socketId = info.sid;
        this.pingIntervalId = setInterval(
            () => this.websocket.send(PACKET_TYPES.PING),
            info.pingInterval
        );
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
        } else if (packetType === PACKET_TYPES.MESSAGE) {
            this._handleMessage(packetData);
        }
    }
}
