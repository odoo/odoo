import { BaseWorker } from "@bus/workers/base_worker";
import { mockWorker } from "@odoo/hoot";
import { MockServer, patchWithCleanup } from "@web/../tests/web_test_helpers";

/**
 * @param {SharedWorker | Worker} worker
 */
function onWorkerConnected(worker) {
    const baseWorker = new BaseWorker(worker.name);
    const client = worker._messageChannel.port2;
    baseWorker.client = client;
    client.addEventListener("message", (ev) => {
        baseWorker.handleMessage(ev);
    });
    client.start();
}

patchWithCleanup(MockServer.prototype, {
    start() {
        mockWorker(onWorkerConnected);
        return super.start(...arguments);
    },
});
