import { browser } from "@web/core/browser/browser";
import { Deferred } from "@web/core/utils/concurrency";
import { EventBus } from "@odoo/owl";

const STATE = Object.freeze({
    INIT: "INIT",
    MASTER: "MASTER",
    REGISTERED: "REGISTERED",
    UNREGISTERED: "UNREGISTERED",
});

export const multiTabSharedWorkerService = {
    dependencies: ["worker_service"],
    start(env, { worker_service: workerService }) {
        const bus = new EventBus();
        let responseDeferred = null;
        let state = STATE.INIT;
        browser.addEventListener("pagehide", unregister);

        function messageHandler(messageEv) {
            const { type, data } = messageEv.data;
            if (!type?.startsWith("ELECTION:")) {
                return;
            }
            switch (type) {
                case "ELECTION:IS_MASTER_RESPONSE":
                    responseDeferred?.resolve(data.answer);
                    responseDeferred = null;
                    break;
                case "ELECTION:HEARTBEAT_REQUEST":
                    workerService.send("ELECTION:HEARTBEAT");
                    break;
                case "ELECTION:ASSIGN_MASTER":
                    state = STATE.MASTER;
                    bus.trigger("become_main_tab");
                    break;
                case "ELECTION:UNASSIGN_MASTER":
                    if (state !== STATE.UNREGISTERED) {
                        state = STATE.REGISTERED;
                    }
                    bus.trigger("no_longer_main_tab");
                    break;
                default:
                    console.warn(
                        "multiTabSharedWorkerService received unknown message type:",
                        type
                    );
            }
        }

        async function startWorker() {
            await workerService.ensureWorkerStarted();
            await workerService.registerHandler(messageHandler);
            workerService.send("ELECTION:REGISTER");
            state = STATE.REGISTERED;
        }

        function unregister() {
            workerService.send("ELECTION:UNREGISTER");
            state = STATE.UNREGISTERED;
        }

        return {
            bus,
            isOnMainTab: async () => {
                if (state === STATE.UNREGISTERED) {
                    return false;
                }
                if (state === STATE.INIT) {
                    await startWorker();
                }
                responseDeferred = new Deferred();
                workerService.send("ELECTION:IS_MASTER?");
                return responseDeferred;
            },
            unregister,
        };
    },
};
