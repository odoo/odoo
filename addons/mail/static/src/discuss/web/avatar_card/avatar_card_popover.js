/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";

    static props = {
        id: { type: Number, required: true },
        relation: { type: String, required: true },
        close: { type: Function, required: true },
    };

    setup() {
        this.orm = useService("orm");
        this.openChat = useOpenChat(this.props.relation);
        onWillStart(async () => {
            [this.user] = await this.orm.read(
                this.props.relation,
                [this.props.id],
                this.fieldNames
            );
        });
    }

    get fieldNames() {
        return ["name", "email", "im_status"];
    }

    onSendClick() {
        this.openChat(this.user.id);
    }
}
