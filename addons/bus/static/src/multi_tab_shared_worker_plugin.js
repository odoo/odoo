import { browser } from "@web/core/browser/browser";
import { EventBus, plugin, Plugin, useListener } from "@odoo/owl";
import { WorkerPlugin } from "@bus/services/worker_plugin";

const STATE = Object.freeze({
    INIT: "INIT",
    MASTER: "MASTER",
    REGISTERED: "REGISTERED",
    UNREGISTERED: "UNREGISTERED",
});

export class MultiTabSharedWorkerPlugin extends Plugin {
    /** @private */
    workerService = plugin(WorkerPlugin);
    bus = new EventBus();
    /**
     * @type {?PromiseWithResolvers<boolean>}
     * @private
     */
    isMasterTabPromWithResolvers = null;
    /** @private */
    state = STATE.INIT;

    setup() {
        useListener(browser, "pagehide", () => this.unregister());
    }

    async isOnMainTab () {
        if (this.state === STATE.UNREGISTERED) {
            return false;
        }
        if (this.state === STATE.INIT) {
            await this.startWorker();
        }
        if (!this.isMasterTabPromWithResolvers) {
            this.isMasterTabPromWithResolvers = Promise.withResolvers();
            this.workerService.send("ELECTION:IS_MASTER?");
        }
        return this.isMasterTabPromWithResolvers.promise;
    }

    /**
     * @private
     */
    messageHandler(messageEv) {
        const { type, data } = messageEv.data;
        if (!type?.startsWith("ELECTION:")) {
            return;
        }
        switch (type) {
            case "ELECTION:IS_MASTER_RESPONSE":
                this.isMasterTabPromWithResolvers?.resolve(data.answer);
                this.isMasterTabPromWithResolvers = null;
                break;
            case "ELECTION:HEARTBEAT_REQUEST":
                this.workerService.send("ELECTION:HEARTBEAT");
                break;
            case "ELECTION:ASSIGN_MASTER":
                this.state = STATE.MASTER;
                this.bus.trigger("become_main_tab");
                break;
            case "ELECTION:UNASSIGN_MASTER":
                if (this.state !== STATE.UNREGISTERED) {
                    this.state = STATE.REGISTERED;
                }
                this.bus.trigger("no_longer_main_tab");
                break;
            default:
                console.warn(
                    "multiTabSharedWorkerService received unknown message type:",
                    type
                );
        }
    }

    /**
     * @private
     */
    async startWorker() {
        await this.workerService.ensureWorkerStarted();
        await this.workerService.registerHandler((ev) => this.messageHandler(ev));
        this.workerService.send("ELECTION:REGISTER");
        this.state = STATE.REGISTERED;
    }

    unregister() {
        this.workerService.send("ELECTION:UNREGISTER");
        this.state = STATE.UNREGISTERED;
    }
}
