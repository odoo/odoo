/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import PortalChatter from '@portal/js/portal_chatter';

/**
 * PortalChatter
 *
 * Extends Frontend Chatter to handle rating count on review tab
 */
PortalChatter.include({
    /**
     * Update review count on review tab in courses
     *
     * @override
     * @private
     */
    _reloadChatterContent: async function (data) {
        await this._super(...arguments);
        if (this.options.res_model === "slide.channel") {
            // TODO: debug
            this.el.querySelector('#review-tab').textContent = _t('Reviews (%s)', data.rating_count);
        }
    },
});
