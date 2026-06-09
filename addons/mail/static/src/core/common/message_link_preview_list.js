import { LinkPreview } from "@mail/core/common/link_preview";

import { Component, props, types } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class MessageLinkPreviewList extends Component {
    static components = { LinkPreview };
    static template = "mail.MessageLinkPreviewList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            messageLinkPreviews: types.array(
                types.instanceOf(this.store["mail.message.link.preview"].Class)
            ),
        });
    }
}
