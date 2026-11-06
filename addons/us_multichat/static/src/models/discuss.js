/** @odoo-module **/

import { registerPatch } from "@mail/model/model_core";

registerPatch({
    name: "Discuss",
    recordMethods: {
        getMLChatCategories() {
            // CategoryMLChat_NAME -> field
            const res = {};
            this.__values.forEach((value, key) => {
                if (key.startsWith("categoryMLChat_")) {
                    res[key] = value;
                }
            });
            return res;
        },
    },
});
