import { Store } from "@mail/core/common/store_service";

import { patch } from '@web/core/utils/patch';

patch(Store.prototype, {
    async getMessagePostParams({ postData }) {
        const params = await super.getMessagePostParams(...arguments);
        if (postData.website_id) {
            params.post_data.website_id = postData.website_id;
        }
        return params;
    },
});
