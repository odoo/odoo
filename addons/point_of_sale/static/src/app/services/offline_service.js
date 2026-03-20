import { offlineService } from "@web/core/offline/offline_service";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

/**
 * Patch the default Odoo offline service to customize behavior for the POS.
 *
 * In the standard implementation, when Odoo detects it is offline,
 * it disables all interactive UI elements (buttons, inputs, etc.)
 * by adding the `disabled` attribute and the `o_disabled_offline` CSS class.
 *
 * However, for the Point of Sale (POS) and Self-Ordering mode, we *want it to
 * remain functional offline*,
 *
 * This patch prevents the offline service from disabling UI components
 */
patch(offlineService, {
    async start() {
        // Skip offline UI disabling if we’re in POS or Self-Ordering mode.
        if (odoo.pos_config_id || session.data?.config_id) {
            return {
                status: {},
                _checkConnection: () => Promise.resolve(),
            };
        }
        return super.start(...arguments);
    },
});
