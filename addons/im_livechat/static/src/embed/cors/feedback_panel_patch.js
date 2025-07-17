import { expirableStorage } from "@im_livechat/core/common/expirable_storage";
import { FeedbackPanel } from "@im_livechat/embed/common/feedback_panel/feedback_panel";
import { GUEST_TOKEN_STORAGE_KEY } from "@im_livechat/embed/common/store_service_patch";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(FeedbackPanel.prototype, {
    get transcriptUrl() {
        const guestToken = expirableStorage.getItem(GUEST_TOKEN_STORAGE_KEY);
        return url(`/im_livechat/cors/download_transcript/${this.props.thread.id}`, {
            guest_token: guestToken,
        });
    },
});
