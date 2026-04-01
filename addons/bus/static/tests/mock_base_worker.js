import { mockWorker } from "@odoo/hoot-mock";
import { MockServer } from "@web/../tests/web_test_helpers";
import { BaseWorker } from "@bus/workers/base_worker";
import { patch } from "@web/core/utils/patch";

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

patch(MockServer.prototype, {
    start() {
        mockWorker(onWorkerConnected);
        return super.start(...arguments);
    },
});
