import { Store } from "@mail/core/common/store_plugin";
import { patchModel } from "@mail/model/export";

export const storePatch = patchModel(Store, {
    async getMessagePostParams({ postData }) {
        const params = await super.getMessagePostParams(...arguments);
        if (postData.rating_value) {
            params.post_data.rating_value = postData.rating_value;
        }
        return params;
    },
});
