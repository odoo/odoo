import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { MultiTabFallbackPlugin } from "./multi_tab_fallback_plugin";
import { MultiTabSharedWorkerPlugin } from "./multi_tab_shared_worker_plugin";
import { plugin } from "@odoo/owl";
import { services } from "@web/core/services";

const Base = browser.SharedWorker ? MultiTabSharedWorkerPlugin : MultiTabFallbackPlugin;

export class MultiTabPlugin extends Base {}

services.add(MultiTabPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the multi_tab service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("multi_tab", {
    start() {
        return plugin(MultiTabPlugin);
    },
});
