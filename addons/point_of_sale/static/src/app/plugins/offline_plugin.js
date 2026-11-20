import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { WebClientOfflinePlugin } from "@web/webclient/offline/webclient_offline_plugin";

const isPos = () => odoo.pos_config_id || session.data?.config_id;

/**
 * In POS / Self-Ordering mode we *want the UI to remain functional offline*.
 *
 * The offline plugins are started automatically by the plugin manager (they are
 * registered as global plugins), so they would otherwise install their listeners
 * and disable interactive UI elements when offline. We neutralize them here by
 * skipping their setup, and disabling the crypto so the offline ORM/many2x
 * caching becomes a no-op.
 */
patch(OfflinePlugin.prototype, {
    setup() {
        if (!isPos()) {
            super.setup();
        }
    },
});

patch(WebClientOfflinePlugin.prototype, {
    setup() {
        if (isPos()) {
            this._crypto = false;
            return;
        }
        super.setup();
    },
});
