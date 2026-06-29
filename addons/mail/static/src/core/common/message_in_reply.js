import { propComputed } from "@mail/utils/common/hooks";

import { Component, props, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

export class MessageInReply extends Component {
    static template = "mail.MessageInReply";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.class = propComputed("class", t.string().optional(""));
        this.message = propComputed("message", t.instanceOf(this.store["mail.message"].Class));
        this.onClick = props.static(
            "onClick",
            t.function([t.instanceOf(this.store["mail.message"].Class)]).optional()
        );
    }

    get authorAvatarUrl() {
        if (
            this.message().message_type &&
            this.message().message_type.includes("email") &&
            !this.message().author_id &&
            !this.message().author_guest_id
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }

        if (this.message().parent_id.author) {
            return this.message().parent_id.author.avatarUrl;
        }

        return this.store.DEFAULT_AVATAR;
    }
}
