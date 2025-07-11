import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { isIosApp } from "@web/core/browser/feature_detection";

export const workerService = {
    dependencies: ["bus.parameters"],

    start(env, { "bus.parameters": params }) {
        let worker;
        let isUsingSharedWorker = browser.SharedWorker && !isIosApp();
        startWorker();

        function startWorker() {
            let workerURL = `${params.serverURL}/bus/websocket_worker_bundle?v=${session.websocket_worker_version}`;
            if (params.serverURL !== window.origin) {
                // Bus service is loaded from a different origin than the bundle
                // URL. The Worker expects an URL from this origin, give it a base64
                // URL that will then load the bundle via "importScripts" which
                // allows cross origin.
                const source = `importScripts("${workerURL}");`;
                workerURL = "data:application/javascript;base64," + window.btoa(source);
            }
            const workerClass = isUsingSharedWorker ? browser.SharedWorker : browser.Worker;
            worker = new workerClass(workerURL, {
                name: isUsingSharedWorker
                    ? "odoo:websocket_shared_worker"
                    : "odoo:websocket_worker",
            });
            worker.addEventListener("error", (e) => {
                if (workerClass === browser.SharedWorker) {
                    console.warn("Error while loading SharedWorker, fallback on Worker.");
                    isUsingSharedWorker = false;
                    startWorker();
                }
            });
            if (isUsingSharedWorker) {
                worker.port.start();
            }
        }

        return {
            /**
             * Register function to handler message from work.
             *
             * @param {function} handler
             */
            registerHandler: (handler) => {
                if (isUsingSharedWorker) {
                    worker.port.addEventListener("message", handler);
                } else {
                    worker.addEventListener("message", handler);
                }
            },
            /**
             * Send a message to the worker.
             *
             * @param {WorkerAction} action Action to be
             * executed by the worker.
             * @param {Object|undefined} data Data required for the action to be
             * executed.
             */
            send: (action, data) => {
                if (!worker) {
                    return;
                }
                const message = { action, data };
                if (isUsingSharedWorker) {
                    worker.port.postMessage(message);
                } else {
                    worker.postMessage(message);
                }
            },
        };
    },
};

registry.category("services").add("worker", workerService);
