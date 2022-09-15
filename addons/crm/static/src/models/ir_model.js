/** @odoo-module **/

import { patchFields } from "@mail/model/model_core";
import "@mail/models/ir_model"; // ensure the model definition is loaded before the patch

patchFields("ir.model", {
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
});
