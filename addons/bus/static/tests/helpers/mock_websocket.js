/** @odoo-module **/

import { WebsocketWorker } from "@bus/workers/websocket_worker";
import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";

class WebSocketMock extends EventTarget {
    constructor() {
        super();
        this.readyState = 0;

        queueMicrotask(() => {
            this.readyState = 1;
            const openEv = new Event("open");
            this.onopen(openEv);
            this.dispatchEvent(openEv);
        });
    }

    close(code = 1000, reason) {
        this.readyState = 3;
        const closeEv = new CloseEvent("close", {
            code,
            reason,
            wasClean: code === 1000,
        });
        this.onclose(closeEv);
        this.dispatchEvent(closeEv);
    }

    onclose(closeEv) {}
    onerror(errorEv) {}
    onopen(openEv) {}

    send(data) {
        if (this.readyState !== 1) {
            const errorEv = new Event("error");
            this.onerror(errorEv);
            this.dispatchEvent(errorEv);
            throw new DOMException("Failed to execute 'send' on 'WebSocket': State is not OPEN");
        }
    }
}

class SharedWorkerMock extends EventTarget {
    constructor(websocketWorker) {
        super();
        this._websocketWorker = websocketWorker;
        this._messageChannel = new MessageChannel();
        this.port = this._messageChannel.port1;
        // port 1 should be started by the service itself.
        this._messageChannel.port2.start();
        this._websocketWorker.registerClient(this._messageChannel.port2);
    }
}

class WorkerMock extends SharedWorkerMock {
    constructor(websocketWorker) {
        super(websocketWorker);
        this.port.start();
        this.postMessage = this.port.postMessage.bind(this.port);
    }
}

let websocketWorker;
QUnit.testDone(() => (websocketWorker = null));
/**
 * @param {*} params Parameters used to patch the websocket worker.
 * @returns {WebsocketWorker} Instance of the worker which will run during the
 * test. Usefull to interact with the worker in order to test the
 * websocket behavior.
 */
export function patchWebsocketWorkerWithCleanup(params = {}) {
    patchWithCleanup(window, {
        WebSocket: function () {
            return new WebSocketMock();
        },
    });
    patchWithCleanup(websocketWorker || WebsocketWorker.prototype, params);
    websocketWorker = websocketWorker || new WebsocketWorker();
    websocketWorker.INITIAL_RECONNECT_DELAY = 0;
    websocketWorker.RECONNECT_JITTER = 0;
    patchWithCleanup(browser, {
        SharedWorker: function () {
            const sharedWorker = new SharedWorkerMock(websocketWorker);
            registerCleanup(() => {
                sharedWorker._messageChannel.port1.close();
                sharedWorker._messageChannel.port2.close();
            });
            return sharedWorker;
        },
        Worker: function () {
            const worker = new WorkerMock(websocketWorker);
            registerCleanup(() => {
                worker._messageChannel.port1.close();
                worker._messageChannel.port2.close();
            });
            return worker;
        },
    });
    registerCleanup(() => {
        if (websocketWorker) {
            clearTimeout(websocketWorker.connectTimeout);
            websocketWorker = null;
        }
    });
    return websocketWorker;
}
