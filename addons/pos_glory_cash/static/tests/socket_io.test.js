import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { waitUntil } from "@odoo/hoot-dom";
import { advanceTime, mockWebSocket } from "@odoo/hoot-mock";
import { SocketIoService } from "@pos_glory_cash/utils/socket_io";

const websocketState = {
    instance: null,
    closed: true,
    received: [],
};

const PING_MESSAGE = "2";
const PONG_MESSAGE = "3";
const OPEN_MESSAGE = '0{"sid":"testSocketId", "pingInterval": 5000}';
const CONNECT_MESSAGE = "40";
const EVENT_MESSAGE = '42["test message"]';
const EVENT_MESSAGE_EMPTY = "42[]";
const EVENT_MESSAGE_BAD_FORMAT = '42"not an array"';
const BINARY_MESSAGE_DATA = new Blob(["test binary data"]);

beforeEach(() => {
    mockWebSocket((ws) => {
        websocketState.instance = ws;
        websocketState.closed = false;
        ws.addEventListener("message", (event) => {
            websocketState.sent.push(event.data);
        });
        ws.addEventListener("close", () => {
            websocketState.closed = true;
        });
    });
});

afterEach(() => {
    websocketState.instance?.close();
    websocketState.instance = null;
    websocketState.sent = [];
    websocketState.closed = true;
});

describe("when open message is received", () => {
    test("sets socket ID from the message", async () => {
        const socketIo = new SocketIoService({});
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(OPEN_MESSAGE);

        expect(socketIo.socketId).toBe("testSocketId");
    });

    test("sends ping request every 5 seconds", async () => {
        const socketIo = new SocketIoService({ onClose: () => {} });
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(OPEN_MESSAGE);
        await advanceTime(11000);

        expect(websocketState.sent).toHaveLength(2);
        expect(websocketState.sent[0]).toBe(PING_MESSAGE);
        expect(websocketState.sent[1]).toBe(PING_MESSAGE);
    });

    test("closes connection if pong response is not received in 10s after ping", async () => {
        const socketIo = new SocketIoService({ onClose: () => {} });
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(OPEN_MESSAGE);
        await advanceTime(6000);
        expect(websocketState.sent).toHaveLength(1);
        expect(websocketState.sent[0]).toBe(PING_MESSAGE);
        await advanceTime(10000);

        expect(websocketState.closed).toBe(true);
    });

    test("keep connection open if pong response is received", async () => {
        const socketIo = new SocketIoService({});
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(OPEN_MESSAGE);
        await advanceTime(1000);
        websocketState.instance.send(PONG_MESSAGE);
        await advanceTime(5000);
        websocketState.instance.send(PONG_MESSAGE);
        await advanceTime(5000);

        expect(websocketState.closed).toBe(false);
    });
});

describe("when connect is called a second time", () => {
    test("closes current connection and opens new connection", async () => {
        const socketIo = new SocketIoService({});
        socketIo.connect("mockUrl");
        const firstWebsocket = websocketState.instance;
        await waitUntil(() => firstWebsocket.readyState);

        socketIo.connect("mockUrl2");
        const secondWebsocket = websocketState.instance;
        await waitUntil(() => secondWebsocket.readyState);

        expect(firstWebsocket.readyState).toBe(WebSocket.CLOSED);
        expect(secondWebsocket.readyState).toBe(WebSocket.OPEN);
    });
});

describe("when connect message is received", () => {
    test("calls onConnect callback", async () => {
        let onConnectCalled = false;
        const socketIo = new SocketIoService({
            onConnect: () => {
                onConnectCalled = true;
            },
        });
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(CONNECT_MESSAGE);

        expect(onConnectCalled).toBe(true);
    });
});

describe("when event message is received", () => {
    test("does not call callback and closes websocket if message is empty", async () => {
        let eventReceived = null;
        const socketIo = new SocketIoService({
            onClose: () => {},
            onEvent: (event) => {
                eventReceived = event;
            },
        });
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(EVENT_MESSAGE_EMPTY);

        await waitUntil(() => websocketState.closed);
        expect(eventReceived).toBe(null);
    });

    test("does not call callback and closes websocket if message is invalid", async () => {
        let eventReceived = null;
        const socketIo = new SocketIoService({
            onClose: () => {},
            onEvent: (event) => {
                eventReceived = event;
            },
        });
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(EVENT_MESSAGE_BAD_FORMAT);

        await waitUntil(() => websocketState.closed);
        expect(eventReceived).toBe(null);
    });

    test("calls onEvent callback if message is valid", async () => {
        let eventReceived = null;
        const socketIo = new SocketIoService({
            onEvent: (event) => {
                eventReceived = event;
            },
        });
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(EVENT_MESSAGE);

        expect(eventReceived).toHaveLength(1);
        expect(eventReceived[0]).toBe("test message");
    });
});

describe("when binary event message is received", () => {
    test("calls onBinaryEvent callback", async () => {
        let eventReceived = null;
        const socketIo = new SocketIoService({
            onBinaryEvent: (data) => {
                eventReceived = data;
            },
        });
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        websocketState.instance.send(BINARY_MESSAGE_DATA);

        expect(eventReceived).toBeInstanceOf(Blob);
        expect(await eventReceived.text()).toBe("test binary data");
    });
});

describe("when sending a message", () => {
    test("the message is sent in the correct format", async () => {
        const socketIo = new SocketIoService({});
        socketIo.connect("mockUrl");
        await waitUntil(() => websocketState.instance.readyState);

        socketIo.sendMessage("test");

        expect(websocketState.sent).toHaveLength(1);
        expect(websocketState.sent[0]).toBe('42["test"]');
    });
});
