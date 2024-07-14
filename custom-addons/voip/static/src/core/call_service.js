/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export class CallService {
    missedCalls = 0;

    constructor(env, services) {
        this.env = env;
        this.orm = services.orm;
        this.store = services["mail.store"];
        this.activityService = services["mail.activity"];
    }

    async abort(call) {
        const [data] = await this.orm.call("voip.call", "abort_call", [[call.id]]);
        this.store.Call.insert(data);
    }

    async create(data) {
        const { activity, partner } = data;
        delete data.activity;
        delete data.partner;
        data.partner_id = partner?.id;
        const [res] = await this.orm.call("voip.call", "create_and_format", [], data);
        const call = this.store.Call.insert(res);
        if (activity) {
            call.activity = activity;
        }
        if (!call.partner) {
            this.orm.call("voip.call", "get_contact_info", [[call.id]]).then((partnerData) => {
                if (partnerData) {
                    call.partner = partnerData;
                }
            });
        }
        return call;
    }

    async end(call, { activityDone = true } = {}) {
        let data;
        if (call.activity && activityDone) {
            [data] = await this.orm.call("voip.call", "end_call", [[call.id]], {
                activity_name: call.activity.res_name,
            });
            await this.activityService.markAsDone(call.activity);
            this.activityService.delete(call.activity);
            call.activity = null;
        } else {
            [data] = await this.orm.call("voip.call", "end_call", [[call.id]]);
        }
        this.store.Call.insert(data);
        if (call.timer) {
            clearInterval(call.timer.interval);
            call.timer = null;
        }
    }

    async miss(call) {
        const [data] = await this.orm.call("voip.call", "miss_call", [[call.id]]);
        this.store.Call.insert(data);
        this.missedCalls++;
    }

    async reject(call) {
        const [data] = await this.orm.call("voip.call", "reject_call", [[call.id]]);
        this.store.Call.insert(data);
    }

    async start(call) {
        const [data] = await this.orm.call("voip.call", "start_call", [[call.id]]);
        this.store.Call.insert(data);
        call.timer = {};
        const computeDuration = () => {
            call.timer.time = Math.floor((luxon.DateTime.now() - call.startDate) / 1000);
        };
        computeDuration();
        call.timer.interval = browser.setInterval(computeDuration, 1000);
    }
}

export const callService = {
    dependencies: ["mail.activity", "mail.persona", "mail.store", "orm"],
    start(env, services) {
        return new CallService(env, services);
    },
};

registry.category("services").add("voip.call", callService);
