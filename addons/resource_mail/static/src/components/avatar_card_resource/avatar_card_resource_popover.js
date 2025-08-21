import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

export class AvatarCardResourcePopover extends AvatarCardPopover {
    static template = "resource_mail.AvatarCardResourcePopover";

    static defaultProps = {
        ...AvatarCardPopover.defaultProps,
        resModel: "resource.resource",
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.openChat = useOpenChat("res.users");
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        [this.record] = await this.orm.call(this.props.resModel, 'get_avatar_card_data', [[this.props.id], this.fieldNames], {});
        await Promise.all(this.loadAdditionalData());
    }

    loadAdditionalData() {
        // To use when overriden in other modules to load additional data, returns promise(s)
        return [];
    }

    get fieldNames() {
        return ["email", "im_status", "name", "phone", "resource_type", "share", "user_id"];
    }

    get name() {
        return this.record.name;
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

    get showViewProfileBtn() {
        return false;
    }

    get userId() {
        return this.record.user_id[0];
    }
}
