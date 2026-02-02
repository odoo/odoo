/** @odoo-module */

import { delay, tick } from "@odoo/hoot-dom";
import {
    mockedCancelAnimationFrame,
    mockedRequestAnimationFrame,
} from "@web/../lib/hoot-dom/helpers/time";
import { isInstanceOf } from "../../hoot-dom/hoot_dom_utils";
import { makeNetworkLogger } from "../core/logger";
import {
    ensureArray,
    getSyncValue,
    isNil,
    MIME_TYPE,
    MockEventTarget,
    setSyncValue,
} from "../hoot_utils";
import { ensureTest } from "../main_runner";

/**
 * @typedef {ResponseInit & {
 *  type?: ResponseType;
 *  url?: string;
 * }} MockResponseInit
 *
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
    Blob,
    BroadcastChannel,
    document,
    fetch,
    FormData,
    Headers,
    Map,
    Math: { floor: $floor, max: $max, min: $min, random: $random },
    Object: {
        assign: $assign,
        create: $create,
        defineProperty: $defineProperty,
        entries: $entries,
    },
    ProgressEvent,
    ReadableStream,
    Request,
    Response,
    Set,
    TextEncoder,
    Uint8Array,
    URL,
    WebSocket,
    XMLHttpRequest,
} = globalThis;
const { parse: $parse, stringify: $stringify } = globalThis.JSON;

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
 *
 * @param {{ headers?: HeadersInit } | undefined} object
 * @param {string} content
 */
function getHeaders(object, content) {
    /** @type {Headers} */
    let headers;
    if (isInstanceOf(object?.headers, Headers)) {
        headers = object.headers;
    } else {
        headers = new Headers(object?.headers);
    }

    if (content && !headers.has(HEADER.contentType)) {
        if (typeof content === "string") {
            headers.set(HEADER.contentType, MIME_TYPE.text);
        } else if (isInstanceOf(content, Blob)) {
            headers.set(HEADER.contentType, MIME_TYPE.blob);
        } else if (isInstanceOf(content, FormData)) {
            headers.set(HEADER.contentType, MIME_TYPE.formData);
        } else {
            headers.set(HEADER.contentType, MIME_TYPE.json);
        }
    }
    return headers;
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
 * Helper used to parse JSON-RPC request/response parameters, and to make their
 * "jsonrpc", "id" and "method" properties non-enumerable, as to make them more
 * inconspicuous in console logs, effectively highlighting the 'params' or 'result'
 * keys.
 *
 * @param {string} stringParams
 */
function parseJsonRpcParams(stringParams) {
    const jsonParams = $assign($create(null), $parse(stringParams));
    if (jsonParams && "jsonrpc" in jsonParams) {
        $defineProperty(jsonParams, "jsonrpc", {
            value: jsonParams.jsonrpc,
            enumerable: false,
        });
        if ("id" in jsonParams) {
            $defineProperty(jsonParams, "id", {
                value: jsonParams.id,
                enumerable: false,
            });
        }
        if ("method" in jsonParams) {
            $defineProperty(jsonParams, "method", {
                value: jsonParams.method,
                enumerable: false,
            });
        }
    }
    return jsonParams;
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

/**
 * @param {Uint8Array<ArrayBuffer> | string} value
 * @returns {Uint8Array<ArrayBuffer>}
 */
function toBytes(value) {
    return isInstanceOf(value, Uint8Array) ? value : new TextEncoder().encode(value);
}

const DEFAULT_URL = "https://www.hoot.test/";
const ENDLESS_PROMISE = new Promise(() => {});
const HEADER = {
    contentLength: "Content-Length",
    contentType: "Content-Type",
};
const R_EQUAL = /\s*=\s*/;
const R_INTERNAL_URL = /^(blob|data):/;
const R_SEMICOLON = /\s*;\s*/;

const requestResponseMixin = {
    async arrayBuffer() {
        return toBytes(this._readValue("arrayBuffer", true)).buffer;
    },
    async blob() {
        const value = this._readValue("blob", false);
        return isInstanceOf(value, Blob) ? value : new MockBlob([value]);
    },
    async bytes() {
        return toBytes(this._readValue("bytes", true));
    },
    async formData() {
        const data = this._readValue("formData", false);
        if (!isInstanceOf(data, FormData)) {
            throw new TypeError("Failed to fetch");
        }
        return data;
    },
    async json() {
        return $parse(this._readValue("json", true));
    },
    async text() {
        return this._readValue("text", true);
    },
};

/** @type {Set<NetworkInstance>} */
const openNetworkInstances = new Set();

/** @type {ReturnType<parseNetworkDelay>} */
let getNetworkDelay = null;
/** @type {(typeof fetch) | null} */
let mockFetchFn = null;
/** @type {((websocket: ServerWebSocket) => any) | null} */
let mockWebSocketConnection = null;
/** @type {((worker: MockSharedWorker | MockWorker) => any)[]} */
const mockWorkerConnections = [];

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupNetwork() {
    // Mocked functions
    mockFetchFn = null;
    mockWebSocketConnection = null;
    mockWorkerConnections.length = 0;

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
    const strInput = String(input);
    const isInternalUrl = R_INTERNAL_URL.test(strInput);
    if (!mockFetchFn) {
        if (isInternalUrl) {
            // Internal URL without mocked 'fetch': directly handled by the browser
            return fetch(input, init);
        }
        throw new Error(
            `Could not fetch "${strInput}": cannot make a request when fetch is not mocked`
        );
    }
    const controller = markOpen(new AbortController());

    init = { ...init };
    init.headers = getHeaders(init, init.body);
    init.method = init.method?.toUpperCase() || (isNil(init.body) ? "GET" : "POST");

    // Allows 'signal' to not be logged with 'logRequest'.
    $defineProperty(init, "signal", {
        value: controller.signal,
        enumerable: false,
    });

    const { logRequest, logResponse } = makeNetworkLogger(init.method, strInput);

    logRequest(() => {
        const readableInit = {
            ...init,
            // Make headers easier to read in the console
            headers: new Map(init.headers),
        };
        if (init.headers.get(HEADER.contentType) === MIME_TYPE.json) {
            return [parseJsonRpcParams(init.body), readableInit];
        } else {
            return [init.body, readableInit];
        }
    });

    if (getNetworkDelay) {
        await getNetworkDelay();
    }

    // keep separate from 'error', as it can be null or undefined even though the
    // callback has thrown an error.
    let failed = false;
    let error, result;
    try {
        result = await mockFetchFn(input, init);
    } catch (err) {
        failed = true;
        error = err;
    }
    if (isOpen(controller)) {
        markClosed(controller);
    } else {
        return ENDLESS_PROMISE;
    }
    if (failed) {
        throw error;
    }

    if (isInternalUrl && isNil(result)) {
        // Internal URL without mocked result: directly handled by the browser
        return fetch(input, init);
    }

    // Result can be a request or the final request value
    const responseHeaders = getHeaders(result, result);

    if (result instanceof MockResponse) {
        // Mocked response
        logResponse(() => {
            const textValue = getSyncValue(result, true);
            return [
                responseHeaders.get(HEADER.contentType) === MIME_TYPE.json
                    ? parseJsonRpcParams(textValue)
                    : textValue,
                result,
            ];
        });
        return result;
    }

    if (isInstanceOf(result, Response)) {
        // Actual fetch
        logResponse(() => ["(go to network tab for request content)", result]);
        return result;
    }

    // Not a response object:
    // Determine the return type based on:
    // - the content type header
    // - or the type of the returned value
    if (responseHeaders.get(HEADER.contentType) === MIME_TYPE.json) {
        // JSON response
        const strBody = $stringify(result ?? null);
        const response = new MockResponse(strBody, {
            headers: responseHeaders,
            statusText: "OK",
            type: "basic",
            url: strInput,
        });
        logResponse(() => [parseJsonRpcParams(strBody), response]);
        return response;
    }

    // Any other type
    const response = new MockResponse(result, {
        headers: responseHeaders,
        statusText: "OK",
        type: "basic",
        url: strInput,
    });
    logResponse(() => [result, response]);
    return response;
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
    ensureTest("mockFetch");
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
    ensureTest("mockWebSocket");
    mockWebSocketConnection = onWebSocketConnected;
}

/**
 * Activates mock Worker and SharedWorker classes:
 *  - actual code fetched by worker URLs will then be handled by `window.fetch`
 *  (see {@link mockFetch});
 *  - the `onWorkerConnected` callback will be called after a worker has been created.
 *
 * @param {typeof mockWorkerConnections[number]} [onWorkerConnected]
 * @example
 *  mockWorker((worker) => {
 *      worker.addEventListener("message", (event) => {
 *         expect.step(event.type);
 *      });
 *  });
 */
export function mockWorker(onWorkerConnected) {
    ensureTest("mockWorker");
    mockWorkerConnections.push(onWorkerConnected);
}

/**
 * @param {Parameters<parseNetworkDelay>} args
 */
export function throttleNetwork(...args) {
    getNetworkDelay = parseNetworkDelay(...args);
}

/**
 * @param {typeof mockFetchFn} fetchFn
 * @param {() => void} callback
 */
export async function withFetch(fetchFn, callback) {
    mockFetchFn = fetchFn;
    const result = await callback();
    mockFetchFn = null;
    return result;
}

export class MockBlob extends Blob {
    constructor(blobParts, options) {
        super(blobParts, options);

        setSyncValue(this, blobParts);
    }

    async arrayBuffer() {
        return toBytes(getSyncValue(this, true)).buffer;
    }

    async bytes() {
        return toBytes(getSyncValue(this, true));
    }

    async stream() {
        const value = getSyncValue(this, true);
        return isInstanceOf(value, ReadableStream) ? value : new ReadableStream(value);
    }

    async text() {
        return getSyncValue(this, true);
    }
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
    static {
        Object.assign(this.prototype, requestResponseMixin);
    }

    /**
     * @param {RequestInfo} input
     * @param {RequestInit} [init]
     */
    constructor(input, init) {
        super(new MockURL(input), init);

        setSyncValue(this, init?.body ?? null);
    }

    clone() {
        const request = new this.constructor(this.url, this);
        setSyncValue(request, getSyncValue(this, false));
        return request;
    }

    /**
     * In tests, requests objects are expected to be read by multiple network handlers.
     * As such, their 'body' isn't consumed upon reading.
     *
     * @protected
     * @param {string} reader
     * @param {boolean} toStringValue
     */
    _readValue(reader, toStringValue) {
        return getSyncValue(this, toStringValue);
    }
}

export class MockResponse extends Response {
    static {
        Object.assign(this.prototype, requestResponseMixin);
    }

    /**
     * @param {BodyInit} body
     * @param {MockResponseInit} [init]
     */
    constructor(body, init) {
        super(body, init);

        if (init?.type) {
            $defineProperty(this, "type", {
                value: init.type,
                configurable: true,
                enumerable: true,
                writable: false,
            });
        }
        if (init?.url) {
            $defineProperty(this, "url", {
                value: String(new MockURL(init.url)),
                configurable: true,
                enumerable: true,
                writable: false,
            });
        }

        setSyncValue(this, body ?? null);
    }

    clone() {
        return new this.constructor(getSyncValue(this, false), this);
    }

    /**
     * Reading the 'body' of a response always consumes it, as opposed to the {@link MockRequest}
     * body.
     *
     * @protected
     * @param {string} reader
     * @param {boolean} toStringValue
     */
    _readValue(reader, toStringValue) {
        if (this.bodyUsed) {
            throw new TypeError(
                `Failed to execute '${reader}' on '${this.constructor.name}': body stream already read`
            );
        }
        $defineProperty(this, "bodyUsed", { value: true, configurable: true, enumerable: true });
        return getSyncValue(this, toStringValue);
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

        for (const onWorkerConnected of mockWorkerConnections) {
            onWorkerConnected(this);
        }
    }
}

export class MockURL extends URL {
    constructor(url, base) {
        super(url, base || mockLocation);
    }
}

export class MockWebSocket extends MockEventTarget {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;
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
            this._logger.logRequest(() => ["connection open"]);

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
        this._logger.logRequest(() => [data]);
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
        this._messageChannel.port1.addEventListener("message", (ev) => {
            this.dispatchEvent(new MessageEvent("message", { data: ev.data }));
        });

        for (const onWorkerConnected of mockWorkerConnections) {
            onWorkerConnected(this);
        }
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
    static {
        // Assign status codes
        Object.assign(this, XMLHttpRequest);
    }

    /**
     * @private
     */
    _method = "GET";
    /**
     * @private
     */
    _readyState = XMLHttpRequest.UNSENT;
    /**
     * @type {Record<string, string>}
     * @private
     */
    _requestHeaders = Object.create(null);
    /**
     * @private
     */
    _requestUrl = "";
    /**
     * @type {Response | null}
     * @private
     */
    _response = null;
    /**
     * @private
     */
    _responseMimeType = "";
    /**
     * @private
     */
    _responseValue = null;

    get readyState() {
        return this._readyState;
    }

    get response() {
        return this._responseValue;
    }

    get responseText() {
        return String(this._responseValue);
    }

    get responseURL() {
        return this._response.url;
    }

    get responseXML() {
        const parser = new DOMParser();
        try {
            return parser.parseFromString(this._responseValue, this._responseMimeType);
        } catch {
            return null;
        }
    }

    get status() {
        return this._response?.status || 0;
    }

    get statusText() {
        return this._readyState >= XMLHttpRequest.LOADING ? "OK" : "";
    }

    /**
     * @type {XMLHttpRequestResponseType}
     */
    responseType = "";
    upload = new MockXMLHttpRequestUpload();

    abort() {
        this._setReadyState(XMLHttpRequest.DONE);
        markClosed(this);
    }

    /** @type {XMLHttpRequest["dispatchEvent"]} */
    dispatchEvent(event) {
        if (!isOpen(this)) {
            return false;
        }
        return super.dispatchEvent(event);
    }

    getAllResponseHeaders() {
        let result = "";
        for (const [key, value] of this._response?.headers || []) {
            result += `${key}: ${value}\r\n`;
        }
        return result;
    }

    /** @type {XMLHttpRequest["getResponseHeader"]} */
    getResponseHeader(name) {
        return this._response?.headers.get(name) || "";
    }

    /** @type {XMLHttpRequest["open"]} */
    open(method, url) {
        markOpen(this);

        this._method = method;
        this._requestUrl = url;
        this._setReadyState(XMLHttpRequest.OPENED);
    }

    /** @type {XMLHttpRequest["overrideMimeType"]} */
    overrideMimeType(mime) {
        this._responseMimeType = mime;
    }

    /** @type {XMLHttpRequest["send"]} */
    async send(body) {
        if (!isOpen(this)) {
            return ENDLESS_PROMISE;
        }
        this._setReadyState(XMLHttpRequest.HEADERS_RECEIVED);

        try {
            this._response = await window.fetch(this._requestUrl, {
                method: this._method,
                body,
                headers: this._requestHeaders,
            });
            this._setReadyState(XMLHttpRequest.LOADING);
            if (!this._responseMimeType) {
                if (this._response.url.startsWith("blob:")) {
                    this._responseMimeType = MIME_TYPE.blob;
                } else {
                    this._responseMimeType = this._response.headers.get(HEADER.contentType);
                }
            }
            if (this._response instanceof MockResponse) {
                // Mock response: get bound value (synchronously)
                this._responseValue = getSyncValue(this._response, false);
            } else if (this._responseMimeType === MIME_TYPE.blob) {
                // Actual "blob:" response: get array buffer
                this._responseValue = await this._response.arrayBuffer();
            } else if (this._responseMimeType === MIME_TYPE.json) {
                // JSON response: get parsed JSON value
                this._responseValue = await this._response.json();
            } else {
                // Anything else: parse response body as text
                this._responseValue = await this._response.text();
            }
            this.dispatchEvent(new ProgressEvent("load"));
        } catch {
            this.dispatchEvent(new ProgressEvent("error"));
        }

        this._setReadyState(XMLHttpRequest.DONE);
        markClosed(this);
    }

    /** @type {XMLHttpRequest["setRequestHeader"]} */
    setRequestHeader(name, value) {
        this._requestHeaders[name] = value;
    }

    /**
     * @private
     * @param {number} readyState
     */
    _setReadyState(readyState) {
        this._readyState = readyState;
        this.dispatchEvent(new Event("readystatechange"));
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
     */
    constructor(websocket, logger) {
        super();

        markOpen(this);

        this._clientWs = websocket;
        this._logger = logger;

        this.addEventListener("close", (ev) => {
            dispatchClose(this._clientWs, ev);
            this._logger.logResponse(() => ["connection closed", ev]);
        });

        mockWebSocketConnection?.(this);
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
