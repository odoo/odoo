import { patch } from "@web/core/utils/patch";

import { Store } from "@mail/core/common/store_service";

patch(Store.prototype, {
    async getMessagePostParams({ body, postData, thread }) {
        const params = await super.getMessagePostParams(
            ...arguments
        );
        if (postData?.notifyInternalFollowers) {
            const ids = (
                (thread?.recipients || [])
                    .filter((r) => {
                        const u = r.partner_id?.main_user_id;
                        return u && !u.share;
                    })
                    .map((r) => r.partner_id.id)
                    .filter(Boolean)
            );
            if (ids.length) {
                const existing = (
                    Array.isArray(params.post_data.partner_ids) ? 
                    params.post_data.partner_ids : []
                );
                params.post_data.partner_ids = [
                    ...new Set([...existing, ...ids]),
                ];
            }
        }
        return params;
    },
});
