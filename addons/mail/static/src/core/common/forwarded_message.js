import { AttachmentList } from "@mail/core/common/attachment_list";

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { MessageLinkPreviewList } from "@mail/core/common/message_link_preview_list";

export class ForwardedMessage extends Component {
    static components = { AttachmentList, MessageLinkPreviewList };
    static props = ["message", "onClick?", "inDialog?"];
    static template = "mail.ForwardedMessage";

    setup() {
        this.store = useService("mail.store");
        this.state = useState({
            displayName: this.props.message.forwarded_from_id?.thread.display_name,
        });
        // debugger
    }

    get isVisible() {
        return this.props.message.forwarded_from_id.thread.selfMember ? true : false;
    }

    get thread() {
        return this.props.message.forwarded_from_id.thread;
    }

    openRecord() {
        const model = this.props.message.forwarded_from_id.thread.model;
        const id = this.props.message.forwarded_from_id.thread.id;
        this.store.Thread.getOrFetch({ model, id }).then((thread) => {
            if (thread) {
                thread.open({ focus: true });
                thread.highlightMessage = this.props.message.forwarded_from_id.id;
            } else {
                this.env.services.notification.add(
                    _t("This thread isn’t available or you can’t access it."),
                    {
                        type: "danger",
                    }
                );
            }
        });
    }
}
