/** @odoo-module */

import { delay, tick } from "@odoo/hoot-dom";
import {
    mockedCancelAnimationFrame,
    mockedRequestAnimationFrame,
} from "@web/../lib/hoot-dom/helpers/time";
import { isInstanceOf } from "../../hoot-dom/hoot_dom_utils";
import { makeNetworkLogger } from "../core/logger";
import { ensureArray, MIME_TYPE, MockEventTarget } from "../hoot_utils";
import { getSyncValue, MockBlob, setSyncValue } from "./sync_values";

/**
 * @typedef {AbortController
 *  | MockBroadcastChannel
 *  | MockMessageChannel
 *  | MockMessagePort
 *  | MockSharedWorker
 *  | MockWebSocket
 *  | MockWorker
 *  | MockXMLHttpRequest
 *  | ServerWebSocket} NetworkInstance
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    AbortController,
    BroadcastChannel,
    document,
    fetch,
    Headers,
    Math: { floor: $floor, max: $max, min: $min, random: $random },
    Object: { assign: $assign, create: $create, entries: $entries },
    ProgressEvent,
    Request,
    Response,
    Set,
    URL,
    WebSocket,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {EventTarget} target
 * @param {CloseEventInit} eventInit
 */
function dispatchClose(target, eventInit) {
    if (!isOpen(target)) {
        return;
    }
    markClosed(target);
    eventInit.code ??= 1000;
    eventInit.wasClean ??= eventInit.code === 1000;
    target.dispatchEvent(new CloseEvent("close", eventInit));
}

/**
 * @param {EventTarget} target
 * @param {any} data
 * @param {Transferable[] | StructuredSerializeOptions} [transfer]
 */
async function dispatchMessage(target, data, transfer) {
    const targets = [];
    if (transfer) {
        targets.push(...(transfer?.transfer || transfer));
    }
    if (!targets.length) {
        targets.push(target);
    }
    const messageEventInit = { data };
    let dispatched = false;
    for (const target of targets) {
        if (isOpen(target)) {
            dispatched = true;
            target.dispatchEvent(new MessageEvent("message", messageEventInit));
        }
    }
    if (dispatched) {
        await tick();
    }
}

/**
 * @param {...NetworkInstance} instances
 */
function isOpen(...instances) {
    return instances.every((i) => openNetworkInstances.has(i));
}

/**
 * @param {...NetworkInstance} instances
 */
function markClosed(...instances) {
    for (const instance of instances) {
        openNetworkInstances.delete(instance);
    }
}

/**
 * @param {NetworkInstance} instance
 * @param {Promise<any> | null} [promise]
 */
function markOpen(instance) {
    openNetworkInstances.add(instance);
    return instance;
}

/**
 * @param {number} min
 * @param {number} [max]
 */
function parseNetworkDelay(min, max) {
    if (min <= 0) {
        return null;
    }
    if (max) {
        if (max < min) {
            [min, max] = [max, min];
        }
        const diff = max - min;
        return () => delay($floor($random() * diff + min));
    } else {
        return () => delay(min);
    }
}

const DEFAULT_URL = "https://www.hoot.test/";
const ENDLESS_PROMISE = new Promise(() => {});
const HEADER = {
    contentType: "Content-Type",
};
const R_EQUAL = /\s*=\s*/;
const R_INTERNAL_URL = /^(blob|data|file):/;
const R_SEMICOLON = /\s*;\s*/;

/** @type {Set<NetworkInstance>} */
const openNetworkInstances = new Set();

/** @type {ReturnType<parseNetworkDelay>} */
let getNetworkDelay = null;
/** @type {(typeof fetch) | null} */
let mockFetchFn = null;
/** @type {((websocket: ServerWebSocket) => any) | null} */
let mockWebSocketConnection = null;
/** @type {((worker: MockSharedWorker | MockWorker) => any) | null} */
let mockWorkerConnection = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupNetwork() {
    // Mocked functions
    mockFetchFn = null;
    mockWebSocketConnection = null;
    mockWorkerConnection = null;

    // Network instances
    for (const instance of openNetworkInstances) {
        if (isInstanceOf(instance, AbortController)) {
            instance.abort();
        } else if (
            instance instanceof MockBroadcastChannel ||
            instance instanceof MockMessagePort ||
            instance instanceof MockWebSocket ||
            instance instanceof ServerWebSocket
        ) {
            instance.close();
        } else if (instance instanceof MockSharedWorker) {
            instance.port.close(); // Will also close `MockMessageChannel` instances
        } else if (instance instanceof MockWorker) {
            instance.terminate();
        }
    }
    openNetworkInstances.clear();

    // Cookie
    mockCookie._jar = $create(null);

    // History
    mockHistory._index = 0;
    mockHistory._stack = [];
    mockHistory.pushState(null, "", mockHistory._location.href);

    // Location
    mockLocation.href = DEFAULT_URL;
}

/** @type {typeof fetch} */
export async function mockedFetch(input, init) {
    if (R_INTERNAL_URL.test(input)) {
        // Internal URL: directly handled by the browser
        return fetch(input, init);
    }
    if (!mockFetchFn) {
        throw new Error("Can't make a request when fetch is not mocked");
    }
    init ||= {};
    const method = init.method?.toUpperCase() || (init.body ? "POST" : "GET");
    const { logRequest, logResponse } = makeNetworkLogger(method, input);

    const controller = markOpen(new AbortController());
    init.signal = controller.signal;

    logRequest(() => (typeof init.body === "string" ? JSON.parse(init.body) : init));

    if (getNetworkDelay) {
        await getNetworkDelay();
    }

    let failed = false;
    let result;
    try {
        result = await mockFetchFn(input, init);
    } catch (err) {
        result = err;
        failed = true;
    }
    if (isOpen(controller)) {
        markClosed(controller);
    } else {
        return ENDLESS_PROMISE;
    }
    if (failed) {
        throw result;
    }

    /** @type {Headers} */
    let headers;
    if (result && isInstanceOf(result.headers, Headers)) {
        headers = result.headers;
    } else if (isInstanceOf(init.headers, Headers)) {
        headers = init.headers;
    } else {
        headers = new Headers(init.headers);
    }

    let contentType = headers.get(HEADER.contentType);

    if (result instanceof MockResponse) {
        // Mocked response
        logResponse(async () => {
            const textValue = getSyncValue(result);
            return contentType === MIME_TYPE.json ? JSON.parse(textValue) : textValue;
        });
        return result;
    }

    if (isInstanceOf(result, Response)) {
        // Actual fetch
        logResponse(() => "(go to network tab for request content)");
        return result;
    }

    // Not a response object:
    // Determine the return type based on:
    // - the content type header
    // - or the type of the returned value
    if (!contentType) {
        if (typeof result === "string") {
            contentType = MIME_TYPE.text;
        } else if (isInstanceOf(result, Blob)) {
            contentType = MIME_TYPE.blob;
        } else {
            contentType = MIME_TYPE.json;
        }
    }

    if (contentType === MIME_TYPE.json) {
        // JSON response
        const strBody = JSON.stringify(result ?? null);
        logResponse(() => result);
        return new MockResponse(strBody, { [HEADER.contentType]: contentType });
    }

    // Any other type (blob / text)
    logResponse(() => result);
    return new MockResponse(result, { [HEADER.contentType]: contentType });
}

/**
 * Mocks the fetch function by replacing it with a given `fetchFn`.
 *
 * The return value of `fetchFn` is used as the response of the mocked fetch, or
 * wrapped in a {@link MockResponse} object if it does not meet the required format.
 *
 * @param {typeof mockFetchFn} [fetchFn]
 * @example
 *  mockFetch((input, init) => {
 *      if (input === "/../web_search_read") {
 *          return { records: [{ id: 3, name: "john" }] };
 *      }
 *      // ...
 *  });
 * @example
 *  mockFetch((input, init) => {
 *      if (input === "/translations") {
 *          const translations = {
 *              "Hello, world!": "Bonjour, monde !",
 *              // ...
 *          };
 *          return new Response(JSON.stringify(translations));
 *      }
 *  });
 */
export function mockFetch(fetchFn) {
    mockFetchFn = fetchFn;
}

/**
 * Activates mock WebSocket classe:
 *  - websocket connections will be handled by `window.fetch` (see {@link mockFetch});
 *  - the `onWebSocketConnected` callback will be called after a websocket has been created.
 *
 * @param {typeof mockWebSocketConnection} [onWebSocketConnected]
 */
export function mockWebSocket(onWebSocketConnected) {
    mockWebSocketConnection = onWebSocketConnected;
}

/**
 * Activates mock Worker and SharedWorker classes:
 *  - actual code fetched by worker URLs will then be handled by `window.fetch`
 *  (see {@link mockFetch});
 *  - the `onWorkerConnected` callback will be called after a worker has been created.
 *
 * @param {typeof mockWorkerConnection} [onWorkerConnected]
 * @example
 *  mockWorker((worker) => {
 *      worker.addEventListener("message", (event) => {
 *         expect.step(event.type);
 *      });
 *  });
 */
export function mockWorker(onWorkerConnected) {
    mockWorkerConnection = onWorkerConnected;
}

/**
 * @param {Parameters<parseNetworkDelay>} args
 */
export function throttleNetwork(...args) {
    getNetworkDelay = parseNetworkDelay(...args);
}

export class MockBroadcastChannel extends BroadcastChannel {
    constructor() {
        super(...arguments);

        markOpen(this);
    }
}

export class MockCookie {
    /**
     * @private
     * @type {Record<string, string>}
     */
    _jar = $create(null);

    get() {
        return $entries(this._jar)
            .map((entry) => entry.join("="))
            .join("; ");
    }

    /**
     * @param {string} value
     */
    set(value) {
        for (const cookie of String(value).split(R_SEMICOLON)) {
            const [key, value] = cookie.split(R_EQUAL);
            if (value !== "kill" && !["path", "max-age"].includes(key)) {
                this._jar[key] = value;
            }
        }
    }
}

export class MockDedicatedWorkerGlobalScope {
    /**
     * @param {SharedWorker | Worker} worker
     */
    constructor(worker) {
        $assign(
            this,
            {
                cancelanimationframe: mockedCancelAnimationFrame,
                onconnect: null,
                requestanimationframe: mockedRequestAnimationFrame,
                self: this,
            },
            worker
        );
        if (!("close" in this)) {
            this.close = worker.terminate.bind(worker);
        }
    }
}

export class MockHistory {
    /**
     * @private
     */
    _index = 0;
    /**
     * @private
     * @type {Location}
     */
    _location;
    /**
     * @private
     * @type {[any, string][]}
     */
    _stack = [];

    /** @type {History["length"]} */
    get length() {
        return this._stack.length;
    }

    /** @type {History["state"]} */
    get state() {
        const entry = this._stack[this._index];
        return entry && entry[0];
    }

    /** @type {History["scrollRestoration"]} */
    get scrollRestoration() {
        return "auto";
    }

    /**
     * @param {Location} location
     */
    constructor(location) {
        this._location = location;
        this.pushState(null, "", this._location.href);
    }

    /** @type {History["back"]} */
    back() {
        this._index = $max(0, this._index - 1);
        this._location.assign(this._stack[this._index][1]);
        this._dispatchPopState();
    }

    /** @type {History["forward"]} */
    forward() {
        this._index = $min(this._stack.length - 1, this._index + 1);
        this._location.assign(this._stack[this._index][1]);
        this._dispatchPopState();
    }

    /** @type {History["go"]} */
    go(delta) {
        this._index = $max(0, $min(this._stack.length - 1, this._index + delta));
        this._location.assign(this._stack[this._index][1]);
        this._dispatchPopState();
    }

    /** @type {History["pushState"]} */
    pushState(data, unused, url) {
        this._stack = this._stack.slice(0, this._index + 1);
        this._index = this._stack.push([data ?? null, url]) - 1;
        this._location.assign(url);
    }

    /** @type {History["replaceState"]} */
    replaceState(data, unused, url) {
        this._stack[this._index] = [data ?? null, url];
        this._location.assign(url);
    }

    /**
     * @private
     */
    _dispatchPopState() {
        window.dispatchEvent(new PopStateEvent("popstate", { state: this.state }));
    }
}

export class MockLocation extends MockEventTarget {
    static publicListeners = ["reload"];

    /**
     * @private
     */
    _anchor = document.createElement("a");

    get ancestorOrigins() {
        return [];
    }

    get hash() {
        return this._anchor.hash;
    }
    set hash(value) {
        this._anchor.hash = value;
    }

    get host() {
        return this._anchor.host;
    }
    set host(value) {
        this._anchor.host = value;
    }

    get hostname() {
        return this._anchor.hostname;
    }
    set hostname(value) {
        this._anchor.hostname = value;
    }

    get href() {
        return this._anchor.href;
    }
    set href(value) {
        this._anchor.href = value;
    }

    get origin() {
        return this._anchor.origin;
    }
    set origin(value) {
        this._anchor.origin = value;
    }

    get pathname() {
        return this._anchor.pathname;
    }
    set pathname(value) {
        this._anchor.pathname = value;
    }

    get port() {
        return this._anchor.port;
    }
    set port(value) {
        this._anchor.port = value;
    }

    get protocol() {
        return this._anchor.protocol;
    }
    set protocol(value) {
        this._anchor.protocol = value;
    }

    get search() {
        return this._anchor.search;
    }
    set search(value) {
        this._anchor.search = value;
    }

    constructor() {
        super();

        this.href = DEFAULT_URL;
    }

    assign(url) {
        this.href = url;
    }

    reload() {
        this.dispatchEvent(new CustomEvent("reload"));
    }

    replace(url) {
        this.href = url;
    }

    toString() {
        return this._anchor.toString();
    }
}

export class MockMessageChannel {
    /**
     * @protected
     */
    _mutex = Promise.resolve();

    constructor() {
        markOpen(this);

        this.port1 = new MockMessagePort(this);
        this.port2 = new MockMessagePort(this);
        this.port1._target = this.port2;
        this.port2._target = this.port1;
    }
}

export class MockMessagePort extends MockEventTarget {
    static publicListeners = ["error", "message"];

    /**
     * @private
     * @type {MessageChannel}
     */
    _owner;
    /**
     * @private
     * @type {MockMessagePort}
     */
    _target = this;

    /**
     * @param {MessageChannel} owner
     */
    constructor(owner) {
        super();

        this._owner = owner;
    }

    /** @type {MessagePort["close"]} */
    close() {
        // Closing a message port also closes its sibling port & parent channel.
        markClosed(this, this._target, this._owner);
    }

    /** @type {MessagePort["postMessage"]} */
    postMessage(message, transfer) {
        if (!isOpen(this, this._owner, this._target)) {
            return;
        }
        if (this._owner._mutex) {
            this._owner._mutex = this._owner._mutex.then(() =>
                dispatchMessage(this._target, message, transfer)
            );
        } else {
            dispatchMessage(this._target, message, transfer);
        }
    }

    /** @type {MessagePort["start"]} */
    start() {
        markOpen(this);
    }
}

export class MockRequest extends Request {
    /**
     * @param {RequestInfo} input
     * @param {RequestInit} [init]
     */
    constructor(input, init) {
        super(input, init);

        setSyncValue(this, init?.body ?? null);
    }

    async arrayBuffer() {
        return new TextEncoder().encode(getSyncValue(this));
    }

    async blob() {
        return new MockBlob([getSyncValue(this)]);
    }

    async json() {
        return JSON.parse(getSyncValue(this));
    }

    async text() {
        return getSyncValue(this);
    }
}

export class MockResponse extends Response {
    /**
     * @param {BodyInit} body
     * @param {ResponseInit} [init]
     */
    constructor(body, init) {
        super(body, init);

        setSyncValue(this, body ?? null);
    }

    async arrayBuffer() {
        return new TextEncoder().encode(getSyncValue(this)).buffer;
    }

    async blob() {
        return new MockBlob([getSyncValue(this)]);
    }

    async json() {
        return JSON.parse(getSyncValue(this));
    }

    async text() {
        return getSyncValue(this);
    }
}

export class MockSharedWorker extends MockEventTarget {
    static publicListeners = ["error"];

    /**
     * @private
     */
    _messageChannel = new MockMessageChannel();

    get port() {
        return this._messageChannel.port1;
    }

    /**
     * @param {string | URL} scriptURL
     * @param {WorkerOptions} [options]
     */
    constructor(scriptURL, options) {
        super();

        markOpen(this);

        this.url = String(scriptURL);
        this.name = options?.name || "";

        // First port has to be started manually
        this._messageChannel.port2.start();

        mockWorkerConnection?.(this);
    }
}

export class MockURL extends URL {
    constructor(url, base) {
        super(url, base || mockLocation);
    }
}

export class MockWebSocket extends MockEventTarget {
    static publicListeners = ["close", "error", "message", "open"];

    /**
     * @private
     * @type {ServerWebSocket}
     */
    _serverWs;
    /**
     * @private
     * @type {ReturnType<typeof makeNetworkLogger>}
     */
    _logger = null;
    /**
     * @private
     */
    _readyState = WebSocket.CONNECTING;

    get readyState() {
        return this._readyState;
    }

    /**
     * @param {string | URL} url
     * @param {string | string[]} [protocols]
     */
    constructor(url, protocols) {
        super();

        this.url = String(url);
        this.protocols = ensureArray(protocols || []);

        this._logger = makeNetworkLogger("WS", this.url);
        this._serverWs = new ServerWebSocket(this, this._logger);

        this.addEventListener("close", (ev) => {
            this._readyState = WebSocket.CLOSED;
            dispatchClose(this._serverWs, ev);
        });

        tick().then(() => {
            markOpen(this);

            this._readyState = WebSocket.OPEN;
            this._logger.logRequest(() => "connection open");

            this.dispatchEvent(new Event("open"));
        });
    }

    /** @type {WebSocket["close"]} */
    close(code, reason) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this._readyState = WebSocket.CLOSING;
        tick().then(() => dispatchClose(this, { code, reason }));
    }

    /** @type {WebSocket["send"]} */
    send(data) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this._logger.logRequest(() => data);
        dispatchMessage(this._serverWs, data);
    }
}

export class MockWorker extends MockEventTarget {
    static publicListeners = ["error", "message"];

    /**
     * @private
     */
    _messageChannel = new MockMessageChannel();

    /**
     * @param {string | URL} scriptURL
     * @param {WorkerOptions} [options]
     */
    constructor(scriptURL, options) {
        super();

        markOpen(this);

        this.url = String(scriptURL);
        this.name = options?.name || "";

        this._messageChannel.port1.start();
        this._messageChannel.port2.start();

        mockWorkerConnection?.(this);
    }

    /** @type {Worker["postMessage"]} */
    postMessage(message, transfer) {
        if (!isOpen(this, this._messageChannel.port1)) {
            return;
        }
        this._messageChannel.port1.postMessage(message, transfer);
    }

    /** @type {Worker["terminate"]} */
    terminate() {
        if (!isOpen(this, this._messageChannel.port1)) {
            return;
        }
        this._messageChannel.port1.close();

        markClosed(this);
    }
}

export class MockXMLHttpRequest extends MockEventTarget {
    static publicListeners = ["error", "load"];

    /**
     * @private
     */
    _headers = {};
    /**
     * @private
     */
    _method = "GET";
    /**
     * @private
     */
    _response = null;
    /**
     * @private
     */
    _status = XMLHttpRequest.UNSENT;
    /**
     * @private
     */
    _url = "";

    abort() {
        markClosed(this);
    }

    upload = new MockXMLHttpRequestUpload();

    get response() {
        return this._response;
    }

    get status() {
        return this._status;
    }

    /** @type {XMLHttpRequest["dispatchEvent"]} */
    dispatchEvent(event) {
        if (!isOpen(this)) {
            return false;
        }
        return super.dispatchEvent(event);
    }

    /** @type {XMLHttpRequest["open"]} */
    open(method, url) {
        markOpen(this);

        this._method = method;
        this._url = url;
    }

    /** @type {XMLHttpRequest["send"]} */
    async send(body) {
        if (!isOpen(this)) {
            return ENDLESS_PROMISE;
        }

        try {
            const response = await window.fetch(this._url, {
                method: this._method,
                body,
                headers: this._headers,
            });
            this._status = response.status;
            if (new URL(this._url, mockLocation.origin).protocol === "blob:") {
                this._response = await response.arrayBuffer();
            } else {
                this._response = await response.text();
            }
            this.dispatchEvent(new ProgressEvent("load"));
        } catch (error) {
            this.dispatchEvent(new ProgressEvent("error", { error }));
        }

        markClosed(this);
    }

    /** @type {XMLHttpRequest["setRequestHeader"]} */
    setRequestHeader(name, value) {
        this._headers[name] = value;
    }

    /** @type {XMLHttpRequest["getResponseHeader"]} */
    getResponseHeader(name) {
        return this._headers[name];
    }
}

export class MockXMLHttpRequestUpload extends MockEventTarget {
    static publicListeners = [
        "abort",
        "error",
        "load",
        "loadend",
        "loadstart",
        "progress",
        "timeout",
    ];
}

export class ServerWebSocket extends MockEventTarget {
    /**
     * @private
     * @type {MockWebSocket}
     */
    _clientWs;
    /**
     * @private
     * @type {ReturnType<typeof makeNetworkLogger>}
     */
    _logger = null;

    get readyState() {
        return this._clientWs.readyState;
    }

    get url() {
        return this._clientWs.url;
    }

    /**
     * @param {WebSocket} websocket
     * @param {ReturnType<typeof makeNetworkLogger>} logger
     * @param {ReturnType<typeof makeNetworkLogger>} logger
     */
    constructor(websocket, logger) {
        super();

        markOpen(this);

        this._clientWs = websocket;
        this._logger = logger;

        this.addEventListener("close", (ev) => {
            dispatchClose(this._clientWs, ev);
            this._logger.logResponse(() => "connection closed");
        });

        mockWebSocketConnection(this);
        this.dispatchEvent(new Event("open"));
    }

    /** @type {WebSocket["close"]} */
    close(code, reason) {
        dispatchClose(this, { code, reason });
    }

    /** @type {WebSocket["send"]} */
    send(data) {
        if (!isOpen(this)) {
            return;
        }
        this._logger.logResponse(() => data);
        dispatchMessage(this._clientWs, data);
    }
}

export const mockCookie = new MockCookie();
export const mockLocation = new MockLocation();
export const mockHistory = new MockHistory(mockLocation);
