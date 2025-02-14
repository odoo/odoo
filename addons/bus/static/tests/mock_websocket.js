import { after } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { WebsocketWorker } from "@bus/workers/websocket_worker";
import { mockWorker } from "@odoo/hoot-mock";

/** @type {WebsocketWorker | null} */
let websocketWorker = null;

/**
 * @param {Partial<WebsocketWorker>} [params] Parameters used to patch the websocket worker.
 * @returns {WebsocketWorker} Instance of the worker which will run during the
 * test. Usefull to interact with the worker in order to test the
 * websocket behavior.
 */
export function patchWebsocketWorkerWithCleanup(params) {
    if (!websocketWorker) {
        websocketWorker = new WebsocketWorker();
        websocketWorker.INITIAL_RECONNECT_DELAY = 0;
        websocketWorker.RECONNECT_JITTER = 5;
        after(() => {
            clearTimeout(websocketWorker.connectTimeout);
            websocketWorker = null;
        });
    }

    if (params) {
        patchWithCleanup(websocketWorker, params);
    }

    mockWorker((worker) => websocketWorker.registerClient(worker._messageChannel.port2));

    return websocketWorker;
}
