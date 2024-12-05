import { EventBus } from "@odoo/owl";
import { ServerData } from "./server_data";

export class OdooDataProvider extends EventBus {
    constructor(env) {
        super();
        this.orm = env.services.orm.silent;
        this.fieldService = env.services.field;
        this.serverData = new ServerData(this.orm, {
            whenDataStartLoading: (promise) => this.notifyWhenPromiseResolves(promise),
        });
        this.pendingPromises = new Set();
    }

    cancelPromise(promise) {
        this.pendingPromises.delete(promise);
    }

    /**
     * @param {Promise<unknown>} promise
     */
    async notifyWhenPromiseResolves(promise) {
        this.pendingPromises.add(promise);
        await promise
            .then(() => {
                this.pendingPromises.delete(promise);
                this.notify();
            })
            .catch(() => {
                this.pendingPromises.delete(promise);
                this.notify();
            });
    }

    /**
     * Notify that a data source has been updated. Could be useful to
     * request a re-evaluation.
     */
    notify() {
        if (this.pendingPromises.size) {
            if (!this.nextTriggerTimeOutId) {
                // evaluates at least every 10 seconds, even if there are pending promises
                // to avoid blocking everything if there is a really long request
                this.nextTriggerTimeOutId = setTimeout(() => {
                    this.nextTriggerTimeOutId = undefined;
                    if (this.pendingPromises.size) {
                        this.trigger("data-source-updated");
                    }
                }, 10000);
            }
            return;
        }
        this.trigger("data-source-updated");
    }
}
