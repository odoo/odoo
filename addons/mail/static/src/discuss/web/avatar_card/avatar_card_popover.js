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
        this.record = {};
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        [this.record.data] = await this.orm.webRead(this.model, [this.props.id], {
            specification: this.fieldSpecification,
        });
    }

    get fieldNames() {
        return ["name", "email", "phone", "im_status", "share"];
    }

    get fieldSpecification() {
        const fieldSpec = {};
        this.fieldNames.forEach((fieldName) => {
            fieldSpec[fieldName] = {};
        });
        return fieldSpec;
    }

    get model() {
        //TODO: integrate this in props ???
        return "res.users";
    }

    get email() {
        return this.record.data.email;
    }

    get phone() {
        return this.record.data.phone;
    }

    get im_status() {
        return this.record.data.im_status; //TODO: refactor this ? not ideal
    }

    onSendClick() {
        this.openChat(this.record.data.id);
    }
}
