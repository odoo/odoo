/** @odoo-module */
/* eslint-disable no-restricted-syntax */

import { makeNetworkLogger } from "../core/logger";
import { ensureArray, makePublicListeners } from "../hoot_utils";
import { mockedCancelAnimationFrame, mockedRequestAnimationFrame } from "./time";

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    AbortController,
    BroadcastChannel,
    document,
    EventTarget,
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

const BODY_SYMBOL = Symbol("body");
const DEFAULT_URL = "https://www.hoot.test/";
const HEADER = {
    blob: "application/octet-stream",
    contentType: "Content-Type",
    json: "application/json",
    text: "text/plain",
};

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
    for (const worker of openWorkers) {
        if ("port" in worker) {
            worker.port.close();
        } else {
            worker.terminate();
        }
    }
    openWorkers.clear();
    mockWorkerConnection = null;

    // Other APIs
    mockCookie.__clear();
    mockHistory.__clear();
    mockLocation.__clear();
    MockBroadcastChannel.__clear();
}

/** @type {typeof fetch} */
export async function mockedFetch(input, init) {
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
        logResponse(async () =>
            headers.get(HEADER.contentType) === HEADER.json
                ? await result.json()
                : await result.text()
        );
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
    static #instances = [];

    constructor() {
        super(...arguments);

        MockBroadcastChannel.#instances.push(this);
    }

    static __clear() {
        while (MockBroadcastChannel.#instances.length) {
            MockBroadcastChannel.#instances.pop().close();
        }
    }
}

export class MockCookie {
    /** @type {Record<string, string>} */
    #jar = {};

    get() {
        return $entries(this.#jar)
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
                this.#jar[key] = value;
            }
        }
    }

    __clear() {
        this.#jar = {};
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
    #index = 0;
    /** @type {Location} */
    #loc;
    /** @type {[any, string][]} */
    #stack = [];

    /** @type {typeof History.prototype.length} */
    get length() {
        return this.#stack.length;
    }

    /** @type {typeof History.prototype.state} */
    get state() {
        const entry = this.#stack[this.#index];
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
        this.#loc = location;
        this.pushState(null, "", this.#loc.href);
    }

    /** @type {typeof History.prototype.back} */
    back() {
        this.#index = $max(0, this.#index - 1);
        this.#loc.assign(this.#stack[this.#index][1]);
        this.#dispatchPopState();
    }

    /** @type {typeof History.prototype.forward} */
    forward() {
        this.#index = $min(this.#stack.length - 1, this.#index + 1);
        this.#loc.assign(this.#stack[this.#index][1]);
        this.#dispatchPopState();
    }

    /** @type {typeof History.prototype.go} */
    go(delta) {
        this.#index = $max(0, $min(this.#stack.length - 1, this.#index + delta));
        this.#loc.assign(this.#stack[this.#index][1]);
        this.#dispatchPopState();
    }

    /** @type {typeof History.prototype.pushState} */
    pushState(data, unused, url) {
        this.#stack = this.#stack.slice(0, this.#index + 1);
        this.#index = this.#stack.push([data ?? null, url]) - 1;
        this.#loc.assign(url);
    }

    /** @type {typeof History.prototype.replaceState} */
    replaceState(data, unused, url) {
        this.#stack[this.#index] = [data ?? null, url];
        this.#loc.assign(url);
    }

    #dispatchPopState() {
        window.dispatchEvent(new PopStateEvent("popstate", { state: this.state }));
    }

    __clear() {
        this.#index = 0;
        this.#stack = [];
        this.pushState(null, "", this.#loc.href);
    }
}

export class MockLocation {
    #anchor = document.createElement("a");
    /** @type {(() => any)[]} */
    #onReload = [];

    get ancestorOrigins() {
        return [];
    }

    get hash() {
        return this.#anchor.hash;
    }
    set hash(value) {
        this.#anchor.hash = value;
    }

    get host() {
        return this.#anchor.host;
    }
    set host(value) {
        this.#anchor.host = value;
    }

    get hostname() {
        return this.#anchor.hostname;
    }
    set hostname(value) {
        this.#anchor.hostname = value;
    }

    get href() {
        return this.#anchor.href;
    }
    set href(value) {
        this.#anchor.href = value;
    }

    get origin() {
        return this.#anchor.origin;
    }
    set origin(value) {
        this.#anchor.origin = value;
    }

    get pathname() {
        return this.#anchor.pathname;
    }
    set pathname(value) {
        this.#anchor.pathname = value;
    }

    get port() {
        return this.#anchor.port;
    }
    set port(value) {
        this.#anchor.port = value;
    }

    get protocol() {
        return this.#anchor.protocol;
    }
    set protocol(value) {
        this.#anchor.protocol = value;
    }

    get search() {
        return this.#anchor.search;
    }
    set search(value) {
        this.#anchor.search = value;
    }

    constructor() {
        this.href = DEFAULT_URL;
    }

    assign(url) {
        this.href = url;
    }

    onReload(callback) {
        this.#onReload.push(callback);
    }

    reload() {
        for (const callback of this.#onReload) {
            callback();
        }
    }

    replace(url) {
        this.href = url;
    }

    toString() {
        return this.#anchor.toString();
    }

    __clear() {
        this.href = DEFAULT_URL;
    }
}

export class MockMessagePort extends EventTarget {
    /** @type {() => any} */
    #execute;
    /** @type {SharedWorker} */
    #worker;

    /**
     * @param {SharedWorker} worker
     * @param {() => any} execute
     */
    constructor(worker, execute) {
        super();

        this.#worker = worker;
        this.#execute = execute;
        makePublicListeners(this, ["error", "message"]);
    }

    /** @type {typeof MessagePort["prototype"]["close"]} */
    close() {
        openWorkers.delete(this.#worker);
    }

    /** @type {typeof MessagePort["prototype"]["postMessage"]} */
    postMessage(message) {
        openWorkers.get(this.#worker).then(() => {
            if (!openWorkers.has(this.#worker)) {
                return;
            }
            this.dispatchEvent(new MessageEvent("message", { data: message }));
        });
    }

    /** @type {typeof MessagePort["prototype"]["start"]} */
    start() {
        openWorkers.get(this.#worker).then(() => {
            if (!openWorkers.has(this.#worker)) {
                return;
            }
            this.#execute();
        });
    }
}

export class MockRequest extends Request {
    [BODY_SYMBOL] = null;

    /**
     * @param {RequestInfo} input
     * @param {RequestInit} [init]
     */
    constructor(input, init) {
        super(input, init);

        this[BODY_SYMBOL] = init?.body ?? null;
    }

    arrayBuffer() {
        return new TextEncoder().encode(this[BODY_SYMBOL]);
    }

    blob() {
        return new Blob([this[BODY_SYMBOL]]);
    }

    json() {
        return JSON.parse(this[BODY_SYMBOL]);
    }

    text() {
        return this[BODY_SYMBOL];
    }
}

export class MockResponse extends Response {
    [BODY_SYMBOL] = null;

    /**
     * @param {BodyInit} body
     * @param {ResponseInit} [init]
     */
    constructor(body, init) {
        super(body, init);

        this[BODY_SYMBOL] = body ?? null;
    }

    arrayBuffer() {
        return new TextEncoder().encode(this[BODY_SYMBOL]).buffer;
    }

    blob() {
        return new Blob([this[BODY_SYMBOL]]);
    }

    json() {
        return JSON.parse(this[BODY_SYMBOL]);
    }

    text() {
        return this[BODY_SYMBOL];
    }
}

export class MockSharedWorker extends EventTarget {
    /**
     * @param {string | URL} scriptURL
     * @param {WorkerOptions} [options]
     */
    constructor(scriptURL, options) {
        if (!mockWorkerConnection) {
            return new SharedWorker(...arguments);
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
        super(url, base || mockLocation.origin + mockLocation.pathname);
    }
}

export class MockWebSocket extends EventTarget {
    /** @type {ServerWebSocket | null} */
    #serverWs = null;
    /** @type {ReturnType<typeof makeNetworkLogger>} */
    #logger = null;
    #readyState = WebSocket.CONNECTING;

    get readyState() {
        return this.#readyState;
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
        this.#logger = makeNetworkLogger("WS", this.url);
        this.#serverWs = new ServerWebSocket(this, this.#logger);
        makePublicListeners(this, ["close", "error", "message", "open"]);

        this.addEventListener("close", () => openClientWebsockets.delete(this));
        this.#readyState = WebSocket.OPEN;
    }

    /** @type {typeof WebSocket["prototype"]["close"]} */
    close(code, reason) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this.#readyState = WebSocket.CLOSING;
        this.#serverWs.dispatchEvent(new CloseEvent("close", { code, reason }));
        this.#readyState = WebSocket.CLOSED;
        openClientWebsockets.delete(this);
    }

    /** @type {typeof WebSocket["prototype"]["send"]} */
    send(data) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this.#logger.logRequest(() => data);
        this.#serverWs.dispatchEvent(new MessageEvent("message", { data }));
    }
}

export class MockWorker extends EventTarget {
    /**
     * @param {string | URL} scriptURL
     * @param {WorkerOptions} [options]
     */
    constructor(scriptURL, options) {
        if (!mockWorkerConnection) {
            return new Worker(...arguments);
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
    #headers = {};
    #method = "GET";
    #response;
    #status = 0;
    #url = "";

    abort() {}

    upload = new MockXMLHttpRequestUpload();

    get response() {
        return this.#response;
    }

    get status() {
        return this.#status;
    }

    constructor() {
        super(...arguments);

        makePublicListeners(this, ["error", "load"]);
    }

    /** @type {typeof XMLHttpRequest["prototype"]["open"]} */
    open(method, url) {
        this.#method = method;
        this.#url = url;
    }

    /** @type {typeof XMLHttpRequest["prototype"]["send"]} */
    async send(body) {
        try {
            const response = await window.fetch(this.#url, {
                method: this.#method,
                body,
                headers: this.#headers,
            });
            this.#status = response.status;
            this.#response = await response.text();
            this.dispatchEvent(new ProgressEvent("load"));
        } catch (error) {
            this.dispatchEvent(new ProgressEvent("error", { error }));
        }
    }

    /** @type {typeof XMLHttpRequest["prototype"]["setRequestHeader"]} */
    setRequestHeader(name, value) {
        this.#headers[name] = value;
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
    #clientWs = null;
    /** @type {ReturnType<typeof makeNetworkLogger>} */
    #logger = null;
    #readyState = WebSocket.CONNECTING;

    get readyState() {
        return this.#readyState;
    }

    /**
     * @param {WebSocket} websocket
     * @param {ReturnType<typeof makeNetworkLogger>} logger
     */
    constructor(websocket, logger) {
        super(...arguments);
        openServerWebsockets.add(this);

        this.#clientWs = websocket;
        this.#logger = logger;
        this.url = this.#clientWs.url;

        mockWebSocketConnection(this);

        this.#logger.logRequest(() => "connection open");

        this.addEventListener("close", () => openServerWebsockets.delete(this));
        this.#readyState = WebSocket.OPEN;
    }

    /** @type {typeof WebSocket["prototype"]["close"]} */
    close(code, reason) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this.#readyState = WebSocket.CLOSING;
        this.#clientWs.dispatchEvent(new CloseEvent("close", { code, reason }));
        this.#readyState = WebSocket.CLOSED;
        openServerWebsockets.delete(this);
    }

    /** @type {typeof WebSocket["prototype"]["send"]} */
    send(data) {
        if (this.readyState !== WebSocket.OPEN) {
            return;
        }
        this.#logger.logResponse(() => data);
        this.#clientWs.dispatchEvent(new MessageEvent("message", { data }));
    }
}

export const mockCookie = new MockCookie();
export const mockLocation = new MockLocation();
export const mockHistory = new MockHistory(mockLocation);
