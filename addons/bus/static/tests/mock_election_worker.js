import { ElectionWorker } from "@bus/workers/election_worker";
import { mockWorker } from "@odoo/hoot";
import { MockServer, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { getWorkerBundleVersion } from "./mock_websocket";

patchWithCleanup(MockServer.prototype, {
    start() {
        let electionWorker = new ElectionWorker();
        let currentVersion = null;
        mockWorker(function onWorkerConnected(worker) {
            // As in a browser, another version of the bundle is another worker.
            const version = getWorkerBundleVersion(worker);
            if (version && currentVersion && version !== currentVersion) {
                electionWorker = new ElectionWorker();
            }
            currentVersion = version || currentVersion;
            const client = worker._messageChannel.port2;
            client.addEventListener("message", electionWorker.handleMessage.bind(electionWorker));
            client.start();
        });

        return super.start(...arguments);
    },
});
