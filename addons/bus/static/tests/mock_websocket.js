import { after } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { WebsocketWorker } from "@bus/workers/websocket_worker";
import { browser } from "@web/core/browser/browser";

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
/**
 * @param {*} params Parameters used to patch the websocket worker.
 * @returns {WebsocketWorker} Instance of the worker which will run during the
 * test. Usefull to interact with the worker in order to test the
 * websocket behavior.
 */
export function patchWebsocketWorkerWithCleanup(params = {}) {
    patchWithCleanup(websocketWorker || WebsocketWorker.prototype, params);
    websocketWorker = websocketWorker || new WebsocketWorker();
    websocketWorker.INITIAL_RECONNECT_DELAY = 0;
    websocketWorker.RECONNECT_JITTER = 5;
    patchWithCleanup(browser, {
        SharedWorker: function () {
            const sharedWorker = new SharedWorkerMock(websocketWorker);
            after(() => {
                sharedWorker._messageChannel.port1.close();
                sharedWorker._messageChannel.port2.close();
            });
            return sharedWorker;
        },
        Worker: function () {
            const worker = new WorkerMock(websocketWorker);
            after(() => {
                worker._messageChannel.port1.close();
                worker._messageChannel.port2.close();
            });
            return worker;
        },
    });
    after(() => {
        if (websocketWorker) {
            clearTimeout(websocketWorker.connectTimeout);
            websocketWorker = null;
        }
    });
    return websocketWorker;
}
