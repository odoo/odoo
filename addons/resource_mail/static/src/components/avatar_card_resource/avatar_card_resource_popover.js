/** @odoo-module **/

import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";


export class AvatarCardResourcePopover extends AvatarCardPopover {
    static defaultProps = {
        ...AvatarCardPopover.defaultProps,
        recordModel: "resource.resource",
    };

    get fieldSpecification() {
        return {
            name: {},
            user_id: {
                fields: super.fieldSpecification,
            },
        };
    }
    
    get user() {
        return this.record.data.user_id;
    }

    get displayAvatar() {
        return super.displayAvatar && this.user;//or && this.record.data.resource_type === ... ???? ---> Problem here ???? avatar on res.users or resource.resource ???
    }

    onSendClick() {
        this.openChat(this.user.id);
    }
}
