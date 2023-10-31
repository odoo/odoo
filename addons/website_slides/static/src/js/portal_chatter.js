/** @odoo-module **/

import { _t } from 'web.core';
import { PortalChatter } from 'portal.chatter';

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
            $('#review-tab').text(_.str.sprintf(_t('Reviews (%d)'), data.rating_count));
        }
    },
});
