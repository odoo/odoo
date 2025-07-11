import { Deferred } from "@web/core/utils/concurrency";
import { EventBus } from "@odoo/owl";

export const electionWorkerService = {
    dependencies: ["worker"],
    start(env, { worker }) {
        const bus = new EventBus();
        worker.registerHandler(messageHandler);
        let responseDeferred = null;
        worker.send("ELECTION:REGISTER");

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
                    worker.send("ELECTION:HEARTBEAT");
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
                worker.send("ELECTION:IS_MASTER?");
                return responseDeferred;
            },
            unregister: () => {
                worker.send("ELECTION:UNREGISTER");
            },
        };
    },
};
