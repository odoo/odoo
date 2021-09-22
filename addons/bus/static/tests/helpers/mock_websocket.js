/** @odoo-module **/

import { WebsocketWorker } from "@bus/workers/websocket_worker";
import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";

class WebSocketMock extends EventTarget {
    constructor(url) {
        super();
        this.readyState = 0;
        this.url = url;

        queueMicrotask(() => {
            this.readyState = 1;
            const openEv = new Event('open');
            this.onopen(openEv);
            this.dispatchEvent(openEv);
        });
    }

    close(code, reason) {
        this.readyState = 3;
        const closeEv = new CloseEvent('close', {
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
            const errorEv = new Event('error');
            this.onerror(errorEv);
            this.dispatchEvent(errorEv);
            throw new DOMException("Failed to execute 'send' on 'WebSocket': State is not OPEN");
        }
    }
}

class SharedWorkerMock {
    constructor(websocketWorker) {
        this._websocketWorker = websocketWorker;
        this._messageChannel = new MessageChannel();
        this.port = this._messageChannel.port1;
        // port 1 should be started by the service itself.
        this._messageChannel.port2.start();
        this._websocketWorker.registerClient(this._messageChannel.port2);
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
    patchWithCleanup(window, {
        WebSocket: function () {
            return new WebSocketMock();
        },
    }, { pure: true });
    patchWithCleanup(websocketWorker || WebsocketWorker.prototype, params);
    websocketWorker = websocketWorker || new WebsocketWorker('wss://odoo.com/websocket');
    patchWithCleanup(browser, {
        SharedWorker: function () {
            return new SharedWorkerMock(websocketWorker);
        },
    }, { pure: true });
    registerCleanup(() => {
        clearTimeout(websocketWorker.connectTimeout);
        websocketWorker = null;
    });
    return websocketWorker;
}
