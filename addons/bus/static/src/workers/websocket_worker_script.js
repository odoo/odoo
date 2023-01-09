/** @odoo-module **/
/* eslint-env worker */
/* eslint-disable no-restricted-globals */

import { WebsocketWorker } from "./websocket_worker";

(function () {
    const websocketWorker = new WebsocketWorker(
        `${self.location.protocol === 'https:' ? 'wss' : 'ws'}://${self.location.host}/websocket`
    );

    if (self.name.includes('shared')) {
        // The script is running in a shared worker: let's register every
        // tab connection to the worker in order to relay notifications
        // coming from the websocket.
        onconnect = function (ev) {
            const currentClient = ev.ports[0];
            websocketWorker.registerClient(currentClient);
        };
    } else {
        // The script is running in a simple web worker.
        websocketWorker.registerClient(self);
    }
})();

