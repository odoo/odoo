/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "ir.model",
    fields: {
        availableWebViews: {
            compute() {
                if (this.model === "crm.lead") {
                    return [
                        'list',
                        'kanban',
                        'form',
                        'calendar',
                        'pivot',
                        'graph',
                        'activity',
                    ];
                }
                return this._super();
            },
        },
    },
});
