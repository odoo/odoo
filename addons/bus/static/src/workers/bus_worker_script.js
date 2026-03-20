/* eslint-env worker */
/* eslint-disable no-restricted-globals */

import { BaseWorker } from "./base_worker";
import { ElectionWorker } from "./election_worker";
import { WebsocketWorker } from "./websocket_worker";

(function () {
    const baseWorker = new BaseWorker(self.name);
    const websocketWorker = new WebsocketWorker(self.name);
    const electionWorker = new ElectionWorker();

    if (self.name.includes("shared")) {
        // The script is running in a shared worker.
        onconnect = (ev) => {
            const client = ev.ports[0];
            // Register the base worker to handle first init message.
            // Register the current client for main tab election.
            client.addEventListener("message", (ev) => {
                baseWorker.handleMessage(ev);
                electionWorker.handleMessage(ev);
            });
            // let's register every tab connection to the worker in order to relay
            // notifications coming from the websocket.
            websocketWorker.registerClient(client);
            client.start();
        };
    } else {
        // The script is running in a simple web worker.
        self.addEventListener("message", (ev) => baseWorker.handleMessage(ev));
        websocketWorker.registerClient(self);
    }
})();
