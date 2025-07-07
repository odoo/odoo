/* eslint-env worker */
/* eslint-disable no-restricted-globals */

import { ElectionWorker } from "./election_worker";
import { WebsocketWorker } from "./websocket_worker";

(function () {
    const websocketWorker = new WebsocketWorker(self.name);
    const electionWorker = new ElectionWorker(self.name);

    if (self.name.includes("shared")) {
        // The script is running in a shared worker: let's register every
        // tab connection to the worker in order to relay notifications
        // coming from the websocket.
        onconnect = function (ev) {
            const currentClient = ev.ports[0];
            websocketWorker.registerClient(currentClient);
        };
        // Register the current client for main tab election.
        addEventListener("connect", (ev) => {
            const currentClient = ev.ports[0];
            currentClient.addEventListener("message", (ev) => {
                electionWorker.handleElectionMessage(ev);
            });
            currentClient.start();
        });
    } else {
        // The script is running in a simple web worker.
        websocketWorker.registerClient(self);
    }
})();
