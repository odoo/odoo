/** @odoo-module **/

import { registry } from "@web/core/registry";

export const lazyColumnService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let groupedIDs = [];
        let isCallScheduled = false;
        let prom;
        return {
            async call(id, model, fields) {
                groupedIDs.push(id);
                if (!isCallScheduled) {
                    isCallScheduled = true;
                    await Promise.resolve(); // wait for a tick to batch all ids
                    const ids = groupedIDs;
                    prom = orm.read(model, ids, [
                        ...fields,
                    ]);
                    groupedIDs = [];
                    isCallScheduled = false;
                }
                await Promise.resolve(); // wait for the prom to be created
                const result = await prom;
                return result ? result.find((item) => item["id"] == id) : false;
            },
        };
    },
};

registry.category("services").add("lazy_column_loading", lazyColumnService);
