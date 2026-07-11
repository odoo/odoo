import { patch } from '@web/core/utils/patch';

import { Store } from '@mail/core/common/store_service';

/** Add internal followers as recipients when posting a note that targets them. */
patch(Store.prototype, {
    /**
     * Merge non-shared internal follower partner ids into the post recipients.
     * @returns {Promise<object>} the message post parameters
     */
    async getMessagePostParams({ postData, thread }) {
        const params = await super.getMessagePostParams(...arguments);
        if (postData?.notifyInternalFollowers) {
            const ids = (thread?.recipients || [])
                .filter((r) => {
                    const u = r.partner_id?.main_user_id;
                    return u && !u.share;
                })
                .map((r) => r.partner_id.id)
                .filter(Boolean);
            if (ids.length) {
                const existing = Array.isArray(params.post_data.partner_ids)
                    ? params.post_data.partner_ids
                    : [];
                params.post_data.partner_ids = [...new Set([...existing, ...ids])];
            }
        }
        return params;
    },
});
