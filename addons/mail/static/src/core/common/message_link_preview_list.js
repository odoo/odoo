import { LinkPreview } from "@mail/core/common/link_preview";
import { propComputed } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class MessageLinkPreviewList extends Component {
    static components = { LinkPreview };
    static template = "mail.MessageLinkPreviewList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.messageLinkPreviews = propComputed(
            "messageLinkPreviews",
            t.array(t.instanceOf(this.store["mail.message.link.preview"]))
        );
    }
}
