/** @odoo-module */

import {
    mockedCancelAnimationFrame,
    mockedRequestAnimationFrame,
} from "@web/../lib/hoot-dom/helpers/time";
import { makeNetworkLogger } from "../core/logger";
import { ensureArray, makePublicListeners } from "../hoot_utils";
import { getSyncValue, MockBlob, setSyncValue } from "./sync_values";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    AbortController,
    BroadcastChannel,
    document,
    EventTarget,
    fetch,
    Headers,
    Map,
    Math: { max: $max, min: $min },
    Object: { assign: $assign, entries: $entries, fromEntries: $fromEntries },
    ProgressEvent,
    Request,
    Response,
    Set,
    SharedWorker,
    URL,
    WebSocket,
    Worker,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {SharedWorker | Worker} worker
 */
const makeWorkerScope = (worker) => {
    const execute = async () => {
        const scope = new MockDedicatedWorkerGlobalScope(worker);
        const keys = Reflect.ownKeys(scope);
        const values = $fromEntries(keys.map((key) => [key, globalThis[key]]));
        $assign(globalThis, scope);

        script(scope);
        mockWorkerConnection(worker);

        if (typeof globalThis.onconnect === "function") {
            globalThis.onconnect();
        }

        $assign(globalThis, values);
    };

    const load = async () => {
        await Promise.resolve();

        const response = await globalThis.fetch(worker.url);
        const content = await response.text();
        script = new Function("self", content);
    };

    let script = () => {};

    return { execute, load };
};

const DEFAULT_URL = "https://www.hoot.test/";
const HEADER = {
    blob: "application/octet-stream",
    contentType: "Content-Type",
    json: "application/json",
    text: "text/plain",
};
const R_INTERNAL_URL = /^(blob|file):/;

/** @type {Set<WebSocket>} */
const openClientWebsockets = new Set();
/** @type {Set<AbortController>} */
const openRequestControllers = new Set();
/** @type {Set<ServerWebSocket>} */
const openServerWebsockets = new Set();
/** @type {Map<SharedWorker | Worker, Promise<any>>} */
const openWorkers = new Map();

/** @type {(typeof fetch) | null} */
let mockFetchFn = null;
/** @type {((worker: Worker | MessagePort) => any) | null} */
let mockWorkerConnection = null;
/** @type {((websocket: ServerWebSocket) => any) | null} */
let mockWebSocketConnection = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

export function cleanupNetwork() {
    // Requests
    for (const controller of openRequestControllers) {
        controller.abort();
    }
    openRequestControllers.clear();
    mockFetchFn = null;

    // Websockets
    for (const ws of openServerWebsockets) {
        ws.close();
    }
    openServerWebsockets.clear();
    mockWebSocketConnection = null;

    // Workers
    for (const [worker] of openWorkers) {
        if ("port" in worker) {
            worker.port.close();
        } else {
            worker.terminate();
        }
    }
    openWorkers.clear();
    mockWorkerConnection = null;

    // Other APIs
    mockCookie._clear();
    mockHistory._clear();
    mockLocation._clear();
    MockBroadcastChannel._clear();
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

    const controller = new AbortController();
    init.signal = controller.signal;

    logRequest(() => (typeof init.body === "string" ? JSON.parse(init.body) : init));

    openRequestControllers.add(controller);
    let failed = false;
    let result;
    try {
        result = await mockFetchFn(input, init);
    } catch (err) {
        result = err;
        failed = true;
    }
    if (!openRequestControllers.has(controller)) {
        return new Promise(() => {});
    }
    openRequestControllers.delete(controller);
    if (failed) {
        throw result;
    }

    /** @type {Headers} */
    let headers;
    if (result && result.headers instanceof Headers) {
        headers = result.headers;
    } else if (init.headers instanceof Headers) {
        headers = init.headers;
    } else {
        headers = new Headers(init.headers);
    }

    if (result instanceof MockResponse) {
        // Mocked response
        logResponse(async () => {
            const textValue = getSyncValue(result);
            return headers.get(HEADER.contentType) === HEADER.json
                ? JSON.parse(textValue)
                : textValue;
        });
        return result;
    }

    if (result instanceof Response) {
        // Actual fetch
        logResponse(() => "(go to network tab for request content)");
        return result;
    }

    if (typeof init.body === "string" && !headers.get(HEADER.contentType)) {
        // String response: considered as plain text
        logResponse(() => init.body);
        return new MockResponse(result, {
            headers: { [HEADER.contentType]: HEADER.text },
        });
    }

    if (result instanceof Blob) {
        // Blob response
        logResponse(() => result);
        return new MockResponse(result, {
            headers: { [HEADER.contentType]: HEADER.blob },
        });
    }

    // Default case: JSON response (i.e. anything that isn't a string)
    const strBody = JSON.stringify(result === undefined ? null : result);
    logResponse(() => JSON.parse(strBody));
    return new MockResponse(strBody, {
        headers: { [HEADER.contentType]: headers.get(HEADER.contentType) || HEADER.json },
    });
}

/**
 * Mocks the fetch function by replacing it with a given `fetchFn`.
 *
 * The return value of `fetchFn` is used as the response of the mocked fetch, or
 * wrapped in a {@link MockResponse} object if it does not meet the required format.
 *
 * Returns the function to restore the original behavior.
 *
 * @param {typeof mockFetchFn} [fetchFn]
 * @example
 *  mockFetch((input, init) => {
 *      if (input === "/../web_search_read") {
 *          return { records: [{ id: 3, name: "john" }] };
 *      }
 *      // ...
 *  }));
 * @example
 *  mockFetch((input, init) => {
 *      if (input === "/translations") {
 *          const translations = {
 *              "Hello, world!": "Bonjour, monde !",
 *              // ...
 *          };
 *          return new Response(JSON.stringify(translations));
 *      }
 *  }));
 */
export function mockFetch(fetchFn) {
    mockFetchFn = fetchFn;
}

/**
 * Activates mock WebSocket classe:
 *  - websocket connections will be handled by `window.fetch` (see {@link mockFetch});
 *  - the `onWebSocketConnected` callback will be called after a websocket has been created.
 *
 * Returns a function to close all remaining websockets and to restore the original
 * behavior.
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
 * Returns a function to close all remaining workers and restore the original behavior.
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

export class MockBroadcastChannel extends BroadcastChannel {
    static _instances = [];

    constructor() {
        super(...arguments);

        MockBroadcastChannel._instances.push(this);
    }

    static _clear() {
        while (MockBroadcastChannel._instances.length) {
            MockBroadcastChannel._instances.pop().close();
        }
    }
}

export class MockCookie {
    /** @type {Record<string, string>} */
    _jar = {};

    get() {
        return $entries(this._jar)
            .filter(([, value]) => value !== "kill")
            .map((entry) => entry.join("="))
            .join("; ");
    }

    /**
     * @param {string} value
     */
    set(value) {
        for (const cookie of String(value).split(/\s*;\s*/)) {
            const [key, value] = cookie.split(/=(.*)/);
            if (!["path", "max-age"].includes(key)) {
                this._jar[key] = value;
            }
        }
    }

    _clear() {
        this._jar = {};
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
    _index = 0;
    /** @type {Location} */
    _loc;
    /** @type {[any, string][]} */
    _stack = [];

    /** @type {typeof History.prototype.length} */
    get length() {
        return this._stack.length;
    }

    /** @type {typeof History.prototype.state} */
    get state() {
        const entry = this._stack[this._index];
        return entry && entry[0];
    }

    /** @type {typeof History.prototype.scrollRestoration} */
    get scrollRestoration() {
        return "auto";
    }

    /**
     * @param {Location} location
     */
    constructor(location) {
        this._loc = location;
        this.pushState(null, "", this._loc.href);
    }

    /** @type {typeof History.prototype.back} */
    back() {
        this._index = $max(0, this._index - 1);
        this._loc.assign(this._stack[this._index][1]);
        this._dispatchPopState();
    }

    /** @type {typeof History.prototype.forward} */
    forward() {
        this._index = $min(this._stack.length - 1, this._index + 1);
        this._loc.assign(this._stack[this._index][1]);
        this._dispatchPopState();
    }

    /** @type {typeof History.prototype.go} */
    go(delta) {
        this._index = $max(0, $min(this._stack.length - 1, this._index + delta));
        this._loc.assign(this._stack[this._index][1]);
        this._dispatchPopState();
    }

    /** @type {typeof History.prototype.pushState} */
    pushState(data, unused, url) {
        this._stack = this._stack.slice(0, this._index + 1);
        this._index = this._stack.push([data ?? null, url]) - 1;
        this._loc.assign(url);
    }

    /** @type {typeof History.prototype.replaceState} */
    replaceState(data, unused, url) {
        this._stack[this._index] = [data ?? null, url];
        this._loc.assign(url);
    }

    _dispatchPopState() {
        window.dispatchEvent(new PopStateEvent("popstate", { state: this.state }));
    }

    _clear() {
        this._index = 0;
        this._stack = [];
        this.pushState(null, "", this._loc.href);
    }
}

export class MockLocation extends EventTarget {
    _anchor = document.createElement("a");
    /** @type {(() => any)[]} */
    _onReload = [];

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

        makePublicListeners(this, ["reload"]);
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

    _clear() {
        this.href = DEFAULT_URL;
    }
}

export class MockMessagePort extends EventTarget {
    /** @type {() => any} */
    _execute;
    /** @type {SharedWorker} */
    _worker;

    /**
     * @param {SharedWorker} worker
     * @param {() => any} execute
     */
    constructor(worker, execute) {
        super();

        this._worker = worker;
        this._execute = execute;
        makePublicListeners(this, ["error", "message"]);
    }

    /** @type {typeof MessagePort["prototype"]["close"]} */
    close() {
        openWorkers.delete(this._worker);
    }

    /** @type {typeof MessagePort["prototype"]["postMessage"]} */
    postMessage(message) {
        openWorkers.get(this._worker).then(() => {
            if (!openWorkers.has(this._worker)) {
                return;
            }
            this.dispatchEvent(new MessageEvent("message", { data: message }));
        });
    }

    /** @type {typeof MessagePort["prototype"]["start"]} */
    start() {
        openWorkers.get(this._worker).then(() => {
            if (!openWorkers.has(this._worker)) {
                return;
            }
            this._execute();
        });
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

export class MockSharedWorker extends EventTarget {
    /**
     * @param {string | URL} scriptURL
     * @param {WorkerOptions} [options]
     */
    constructor(scriptURL, options) {
        if (!mockWorkerConnection) {
            const worker = new SharedWorker(...arguments);
            openWorkers.set(worker, Promise.resolve());
            return worker;
        }

        super();

        const { execute, load } = makeWorkerScope(this);

        this.url = String(scriptURL);
        this.name = options?.name || "";
        this.port = new MockMessagePort(this, execute);
        makePublicListeners(this, ["error"]);

        openWorkers.set(this, load());
    }
}

export class MockURL extends URL {
    constructor(url, base) {
        super(url, base || mockLocation);
    }
}

export class MockWebSocket extends EventTarget {
    /** @type {ServerWebSocket | null} */
    _serverWs = null;
    /** @type {ReturnType<typeof makeNetworkLogger>} */
    _logger = null;
    _readyState = WebSocket.CONNECTING;

    get readyState() {
        return this._readyState;
    }

    /**
     * @param {string | URL} url
     * @param {string | string[]} [protocols]
     */
    constructor(url, protocols) {
        if (!mockWebSocketConnection) {
            return new WebSocket(url, protocols);
        }

        super();
        openClientWebsockets.add(this);

        this.url = String(url);
        this.protocols = ensureArray(protocols || "");
        this._logger = makeNetworkLogger("WS", this.url);
        this._serverWs = new ServerWebSocket(this, this._logger);
        makePublicListeners(this, ["close", "error", "message", "open"]);

        this.addEventListener("close", () => openClientWebsockets.delete(this));
        this._readyState = WebSocket.OPEN;
    }

    /** @type {typeof WebSocket["prototype"]["close"]} */
    close(code, reason) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this._readyState = WebSocket.CLOSING;
        this._serverWs.dispatchEvent(new CloseEvent("close", { code, reason }));
        this._readyState = WebSocket.CLOSED;
        openClientWebsockets.delete(this);
    }

    /** @type {typeof WebSocket["prototype"]["send"]} */
    send(data) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this._logger.logRequest(() => data);
        this._serverWs.dispatchEvent(new MessageEvent("message", { data }));
    }
}

export class MockWorker extends EventTarget {
    /**
     * @param {string | URL} scriptURL
     * @param {WorkerOptions} [options]
     */
    constructor(scriptURL, options) {
        if (!mockWorkerConnection) {
            const worker = new Worker(...arguments);
            openWorkers.set(worker, Promise.resolve());
            return worker;
        }

        super();

        const { execute, load } = makeWorkerScope(this);

        this.url = String(scriptURL);
        this.name = options?.name || "";
        makePublicListeners(this, ["error", "message"]);

        openWorkers.set(this, load().then(execute));
    }

    /** @type {typeof Worker["prototype"]["postMessage"]} */
    postMessage(message) {
        openWorkers.get(this).then(() => {
            if (!openWorkers.has(this)) {
                return;
            }
            this.dispatchEvent(new MessageEvent("message", { data: message }));
        });
    }

    /** @type {typeof Worker["prototype"]["terminate"]} */
    terminate() {
        openWorkers.delete(this);
    }
}

export class MockXMLHttpRequest extends EventTarget {
    _headers = {};
    _method = "GET";
    _response = null;
    _status = 0;
    _url = "";

    abort() {}

    upload = new MockXMLHttpRequestUpload();

    get response() {
        return this._response;
    }

    get status() {
        return this._status;
    }

    constructor() {
        super(...arguments);

        makePublicListeners(this, ["error", "load"]);
    }

    /** @type {typeof XMLHttpRequest["prototype"]["open"]} */
    open(method, url) {
        this._method = method;
        this._url = url;
    }

    /** @type {typeof XMLHttpRequest["prototype"]["send"]} */
    async send(body) {
        try {
            const response = await window.fetch(this._url, {
                method: this._method,
                body,
                headers: this._headers,
            });
            this._status = response.status;
            this._response = await response.text();
            this.dispatchEvent(new ProgressEvent("load"));
        } catch (error) {
            this.dispatchEvent(new ProgressEvent("error", { error }));
        }
    }

    /** @type {typeof XMLHttpRequest["prototype"]["setRequestHeader"]} */
    setRequestHeader(name, value) {
        this._headers[name] = value;
    }
    getResponseHeader() {}
}

export class MockXMLHttpRequestUpload extends EventTarget {
    constructor() {
        super(...arguments);

        makePublicListeners(this, [
            "abort",
            "error",
            "load",
            "loadend",
            "loadstart",
            "progress",
            "timeout",
        ]);
    }
}

export class ServerWebSocket extends EventTarget {
    /** @type {WebSocket | null} */
    _clientWs = null;
    /** @type {ReturnType<typeof makeNetworkLogger>} */
    _logger = null;
    _readyState = WebSocket.CONNECTING;

    get readyState() {
        return this._readyState;
    }

    /**
     * @param {WebSocket} websocket
     * @param {ReturnType<typeof makeNetworkLogger>} logger
     */
    constructor(websocket, logger) {
        super(...arguments);
        openServerWebsockets.add(this);

        this._clientWs = websocket;
        this._logger = logger;
        this.url = this._clientWs.url;

        mockWebSocketConnection(this);

        this._logger.logRequest(() => "connection open");

        this.addEventListener("close", () => openServerWebsockets.delete(this));
        this._readyState = WebSocket.OPEN;
    }

    /** @type {typeof WebSocket["prototype"]["close"]} */
    close(code, reason) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this._readyState = WebSocket.CLOSING;
        this._clientWs.dispatchEvent(new CloseEvent("close", { code, reason }));
        this._readyState = WebSocket.CLOSED;
        openServerWebsockets.delete(this);
    }

    /** @type {typeof WebSocket["prototype"]["send"]} */
    send(data) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this._logger.logResponse(() => data);
        this._clientWs.dispatchEvent(new MessageEvent("message", { data }));
    }
}

export const mockCookie = new MockCookie();
export const mockLocation = new MockLocation();
export const mockHistory = new MockHistory(mockLocation);
