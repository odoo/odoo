/** @odoo-module **/

import { _t } from 'web.core';
import { PortalChatter } from 'portal.chatter';
import { sprintf } from '@web/core/utils/strings';

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
            $('#review-tab').text(sprintf(_t('Reviews (%s)'), data.rating_count));
        }
    },
});
