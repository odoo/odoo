import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

/**
 * In POS / Self-Ordering mode we *want the UI to remain functional offline*.
 *
 * The offline plugin is started automatically by the plugin manager (it is
 * registered as a global plugin), so it would otherwise install its listeners
 * and disable interactive UI elements when offline. We neutralize it here by
 * skipping its setup, and disabling the crypto so its offline ORM/many2x
 * caching becomes a no-op.
 */
patch(OfflinePlugin.prototype, {
    setup() {
        if (odoo.pos_config_id || session.data?.config_id) {
            this._crypto = false;
            return;
        }
        super.setup();
    },
});
