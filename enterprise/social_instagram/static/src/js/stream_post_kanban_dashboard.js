/** @odoo-module **/

import { StreamPostDashboard } from '@social/js/stream_post_kanban_dashboard';

import { patch } from "@web/core/utils/patch";

patch(StreamPostDashboard.prototype, {

    /**
     * Instagram doesn't provide any information on stories.
     *
     * @override
     */
    _hasStories(account) {
        return account.media_type !== 'instagram' && super._hasStories(...arguments);
    },

});
