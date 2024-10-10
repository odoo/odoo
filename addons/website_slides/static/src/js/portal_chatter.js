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
        /**
     * Update values to restrict editing and deleting comments.
     *
     * @param {number} messageIndex
     * @override
     */
    getCommentsData: function (messageIndex) {
        let vals = this._super(...arguments);
        Object.assign(vals, { is_user_manager: this.options.is_user_manager, partner_id: this.options.partner_id});
        return vals;
    },
});
