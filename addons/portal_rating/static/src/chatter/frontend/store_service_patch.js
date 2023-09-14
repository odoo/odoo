import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    async getMessagePostParams({ thread }) {
        const params = await super.getMessagePostParams(...arguments);
        if (params.rating_value) {
            params.post_data.rating_value = params.rating_value;
            delete params.rating_value;
        }
        return params;
    },
});
