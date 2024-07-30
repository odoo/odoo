export class RemoteInterface extends EventTarget {
    constructor(config) {
        super();
        this.config = config;
    }
}
export class RequestError extends Error {
    constructor(message) {
        super(message);
        this.name = "RequestError";
    }
}
export class RemoteConnectionError extends Error {
    constructor(message, cause) {
        super(message);
        this.name = "RemoteConnectionError";
        this.cause = cause;
    }
}

export function dispatchEvent(eventEmitter, eventName, payload) {
    let eventPayload;
    if (payload) {
        eventPayload = { detail: payload };
    }
    eventEmitter.dispatchEvent(new CustomEvent(eventName, eventPayload));
}

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
export const debugValue = localStorage.getItem(COLLABORATION_LOCALSTORAGE_KEY);
export const debugShowLog = ["", "true", "all"].includes(debugValue);

export function debugLog(...args) {
    if (!debugShowLog) {
        return;
    }
    console.warn(...args);
}
