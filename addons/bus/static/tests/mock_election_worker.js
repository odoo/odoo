import { ElectionWorker } from "@bus/workers/election_worker";
import { mockWorker } from "@odoo/hoot";
import { MockServer, patchWithCleanup } from "@web/../tests/web_test_helpers";

patchWithCleanup(MockServer.prototype, {
    start() {
        const electionWorker = new ElectionWorker();
        mockWorker(function onWorkerConnected(worker) {
            const client = worker._messageChannel.port2;
            client.addEventListener("message", electionWorker.handleMessage.bind(electionWorker));
            client.start();
        });

        return super.start(...arguments);
    },
});
