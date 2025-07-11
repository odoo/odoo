import { mockWorker } from "@odoo/hoot-mock";
import { MockServer } from "@web/../tests/web_test_helpers";
import { ElectionWorker } from "@bus/workers/election_worker";
import { patch } from "@web/core/utils/patch";

let electionWorker = null;

/**
 * @param {SharedWorker | Worker} worker
 */
function onWorkerConnected(worker) {
    if (worker.url.includes("websocket_worker")) {
        electionWorker.registerCandidate(worker._messageChannel.port2);
    }
}

function setupElectionWorker() {
    electionWorker = new ElectionWorker();
    mockWorker(onWorkerConnected);
}

patch(MockServer.prototype, {
    start() {
        setupElectionWorker();
        return super.start(...arguments);
    },
});
