/** @odoo-module **/

import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";


export class AvatarCardResourcePopover extends AvatarCardPopover {
    static template = "resource_mail.AvatarCardResourcePopover";

    static props = {
        ...AvatarCardPopover.props,
        recordModel: {
            type: String,
            optional: true,
        },
    };

    static defaultProps = {
        ...AvatarCardPopover.defaultProps,
        recordModel: "resource.resource",
    };

    get fieldNames() {
        return [
            ...super.fieldNames,
            "user_id",
            "resource_type",//TODO: remove this field ??? (in test as well), not used anymore
        ];
    }

    get model() {
        return this.props.recordModel;
    }

    get displayAvatar() {
        return this.record.data.user_id;
    }

    onSendClick() {
        this.openChat(this.record.data.user_id);
    }
}
