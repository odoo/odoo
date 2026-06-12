import { Component, props, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

export class MessageInReply extends Component {
    static template = "mail.MessageInReply";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            class: t.string().optional(""),
            message: t.instanceOf(this.store["mail.message"].Class),
            onClick: t.function([]).optional(),
        });
    }

    get authorAvatarUrl() {
        if (
            this.props.message.message_type &&
            this.props.message.message_type.includes("email") &&
            !this.props.message.author_id &&
            !this.props.message.author_guest_id
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }

        if (this.props.message.parent_id.author) {
            return this.props.message.parent_id.author.avatarUrl;
        }

        return this.store.DEFAULT_AVATAR;
    }
}
