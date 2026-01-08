import { ForwardDialog } from "@mail/core/common/forward_dialog";

import { patch } from "@web/core/utils/patch";

patch(ForwardDialog.prototype, {
    _shouldExcludeThreadForForward(thread) {
        return Boolean(thread.livechat_end_dt) || super._shouldExcludeThreadForForward(thread);
    },
});
