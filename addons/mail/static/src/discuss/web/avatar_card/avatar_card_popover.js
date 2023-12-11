/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";

    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
    };

    setup() {
        this.orm = useService("orm");
        this.openChat = useOpenChat("res.users");
        onWillStart(async () => {
            [this.user] = await this.orm.read("res.users", [this.props.id], this.fieldNames);
        });
    }

    get fieldNames() {
        return ["name", "email", "phone", "im_status", "share"];
    }

    get email() {
        return this.user.email;
    }

    get phone() {
        return this.user.phone;
    }

    onSendClick() {
        this.openChat(this.user.id);
    }
}
