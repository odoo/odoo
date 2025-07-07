import { browser } from "@web/core/browser/browser";
import { Deferred } from "@web/core/utils/concurrency";
import { session } from "@web/session";
import { EventBus } from "@odoo/owl";

export const electionWorkerService = {
    dependencies: ["bus.parameters"],
    start(env, { "bus.parameters": params }) {
        const bus = new EventBus();
        let worker;
        let responseDeferred = null;
        startWorker();

        function startWorker() {
            const workerURL = `${params.serverURL}/bus/websocket_worker_bundle?v=${session.websocket_worker_version}`;
            worker = new browser.SharedWorker(workerURL, {
                name: "odoo:websocket_shared_worker",
            });
            worker.port.start();
            worker.port.addEventListener("message", messageHandler);
            worker.port.postMessage({ type: "ELECTION:REGISTER" });
        }

        function messageHandler(messageEv) {
            const { type, data } = messageEv.data;
            if (!type?.startsWith("ELECTION:")) {
                return;
            }
            console.info("Election service received message:", type, data);
            switch (type) {
                case "ELECTION:MASTER_ID_RESPONSE":
                    if (responseDeferred) {
                        responseDeferred.resolve(data.answer);
                        responseDeferred = null;
                    }
                    break;
                case "ELECTION:HEARTBEAT_REQUEST":
                    worker.port.postMessage({ type: "ELECTION:HEARTBEAT" });
                    break;
                case "ELECTION:ASSIGN_MASTER":
                    console.log("This tab is now the master tab");
                    bus.trigger("become_main_tab");
                    break;
                case "ELECTION:UNASSIGN_MASTER":
                    console.log("This tab is no longer the master tab");
                    bus.trigger("no_longer_main_tab");
                    break;
                default:
                    console.warn("ElectionWorkerService received unknown message type:", type);
            }
        }

        return {
            bus,
            isOnMainTab: async () => {
                responseDeferred = new Deferred();
                worker.port.postMessage({ type: "ELECTION:IS_MASTER?" });
                return responseDeferred;
            },
            unregister: () => {
                worker.port.postMessage({ type: "ELECTION:UNREGISTER" });
            },
        };
    },
};
