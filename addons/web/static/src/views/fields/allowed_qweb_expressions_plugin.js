import { Plugin, usePlugin } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { ORM } from "@web/core/orm_plugin";

export class AllowedQwebExpressionsPlugin extends Plugin {
    /** @private */
    orm = usePlugin(ORM);
    /** @private */
    cache = new Map();

    getAllowedQwebExpressions(resModel) {
        if (this.cache.has(resModel)) {
            return this.cache.get(resModel);
        }
        const prom = this.orm.call(resModel, "mail_allowed_qweb_expressions").catch((e) => {
            this.cache.delete(resModel);
            return Promise.reject(e);
        });
        this.cache.set(resModel, prom);
        return prom;
    }
}

services.add(AllowedQwebExpressionsPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the allowed_qweb_expressions service are removed
 * -----------------------------------------------------------------------------
 */
export const allowedQwebExpressionsService = {
    dependencies: ["orm"],
    start() {
        const plugin = usePlugin(AllowedQwebExpressionsPlugin);
        return plugin.getAllowedQwebExpressions.bind(plugin);
    },
};
registry.category("services").add("allowed_qweb_expressions", allowedQwebExpressionsService);
