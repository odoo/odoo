/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";

    static props = {
        id: { type: Number, required: true },
        recordModel: {
            type: String,
            optional: true,
        },
        close: { type: Function, required: true },
    };

    static defaultProps = {
        recordModel: "res.users",
    };

    setup() {
        this.orm = useService("orm");
        this.openChat = useOpenChat("res.users");
        this.record = {};
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        [this.record.data] = await this.orm.webRead(this.props.recordModel, [this.props.id], {
            specification: this.fieldSpecification,
        });
    }

    get fieldSpecification() {
        return {
            name: {},
            email: {},
            phone: {},
            im_status: {},
            share: {},
        };
    }

    get user() {
        return this.record.data;
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

    get displayAvatar() {
        return this.props.id && this.props.recordModel;
    }
}
