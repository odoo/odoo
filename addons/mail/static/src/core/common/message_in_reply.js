import { Component, t, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

/** @param {import("models").Store} store */
export const onParentMessageClickType = (store) =>
    t.function([
        t.instanceOf(MouseEvent),
        t.object({ parentAtRender: t.instanceOf(store["mail.message"]) }),
    ]);

export class MessageInReply extends Component {
    static template = "mail.MessageInReply";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            class: t.signal(t.string()).optional(""),
            message: t.signal(t.instanceOf(this.store["mail.message"])),
            onClick: onParentMessageClickType(this.store).optional().static(),
        });
    }

    get authorAvatarUrl() {
        if (
            this.props.message().message_type &&
            this.props.message().message_type.includes("email") &&
            !this.props.message().author_id &&
            !this.props.message().author_guest_id
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }

        if (this.props.message().parent_id.author) {
            return this.props.message().parent_id.author.avatarUrl;
        }

        return this.store.DEFAULT_AVATAR;
    }
}
