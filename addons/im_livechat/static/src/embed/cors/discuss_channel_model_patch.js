import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { patchModel } from "@mail/model/export";
import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { GUEST_TOKEN_STORAGE_KEY } from "@im_livechat/embed/common/store_service_patch";

import { url } from "@web/core/utils/urls";

export const discussChannelPatch = patchModel(DiscussChannel, {
    get transcriptUrl() {
        const guestToken = expirableStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
        return url(`/im_livechat/cors/download_transcript/${this.id}`, {
            guest_token: guestToken,
        });
    },
});
