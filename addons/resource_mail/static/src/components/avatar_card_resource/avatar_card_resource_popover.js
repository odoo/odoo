/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
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

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.openChat = useOpenChat("res.users");
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        [this.record] = await this.orm.read(this.props.recordModel, [this.props.id], this.fieldNames);
        await Promise.all(this.loadAdditionalData());
    }

    loadAdditionalData() {
        // To use when overriden in other modules to load additional data, returns promise(s)
        return [];
    }

    get fieldNames() {
        return [
            ...super.fieldNames,
            "user_id",            
            "resource_type",
        ];
    }

    get email() {
        return this.record.email;
    }

    get phone() {
        return this.record.phone;
    }

    get displayAvatar() {
        return this.record.user_id?.length;
    }

    onSendClick() {
        this.openChat(this.record.user_id[0]);
    }
}
