import { proxy } from "@odoo/owl";
import { getOnNotified } from "@point_of_sale/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

/**
 * Recursively updates a reactive target object/array with values from a source object/array in-place.
 * This preserves object/array references to prevent OWL 3 from unnecessarily rebuilding the entire DOM.
 *
 * @param {Object|Array} target - The reactive object to be updated.
 * @param {Object|Array} source - The new data to apply.
 */
function deepUpdate(target, source) {
    for (const key of Object.keys(target)) {
        if (!(key in source)) {
            delete target[key];
        }
    }
    for (const [key, newVal] of Object.entries(source)) {
        const oldVal = target[key];
        if (Array.isArray(newVal) && Array.isArray(oldVal)) {
            for (let i = 0; i < newVal.length; i++) {
                if (i < oldVal.length) {
                    if (
                        typeof newVal[i] === "object" &&
                        newVal[i] !== null &&
                        typeof oldVal[i] === "object" &&
                        oldVal[i] !== null
                    ) {
                        deepUpdate(oldVal[i], newVal[i]);
                    } else if (oldVal[i] !== newVal[i]) {
                        oldVal[i] = newVal[i];
                    }
                } else {
                    oldVal.push(newVal[i]);
                }
            }
            if (oldVal.length > newVal.length) {
                oldVal.length = newVal.length;
            }
        } else if (
            typeof newVal === "object" &&
            newVal !== null &&
            typeof oldVal === "object" &&
            oldVal !== null &&
            !Array.isArray(newVal)
        ) {
            deepUpdate(oldVal, newVal);
        } else if (oldVal !== newVal) {
            target[key] = newVal;
        }
    }
}

export const CustomerDisplayDataService = {
    dependencies: ["bus_service"],
    async start(env, services) {
        return this.setup(...arguments);
    },
    async setup(env, { bus_service }) {
        const data = proxy({});
        new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY").onmessage = (event) => {
            deepUpdate(data, event.data);
        };
        getOnNotified(bus_service, session.access_token)(
            `UPDATE_CUSTOMER_DISPLAY-${session.device_uuid}`,
            (payload) => {
                deepUpdate(data, payload);
            }
        );
        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
