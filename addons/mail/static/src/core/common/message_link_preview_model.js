import { MailMessageLinkPreview } from "@mail/core/common/model_definitions";

import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(MailMessageLinkPreview.prototype, {
    get gifPaused() {
        return !this.message_id.thread?.isFocused;
    },
    hide() {
        rpc("/mail/link_preview/hide", { message_link_preview_ids: [this.id] });
    },
});
