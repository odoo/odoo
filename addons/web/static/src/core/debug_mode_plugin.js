import { Plugin } from "@odoo/owl";
import { services } from "@web/core/services";

export class DebugModePlugin extends Plugin {
    /**
     * @param {string} [mode]
     */
    isActive(mode) {
        const activeMode = this.toString();
        return Boolean(activeMode) && (!mode || activeMode.includes(mode));
    }

    toList() {
        const str = this.toString();
        if (!str) {
            return [];
        }
        return str.split(",");
    }

    toString() {
        return odoo.debug || "";
    }
}
services.add(DebugModePlugin);
