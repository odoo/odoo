import { onWillStart, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

export class AvatarCardResourcePopover extends AvatarCardPopover {
    static template = "resource_mail.AvatarCardResourcePopover";

    static props = {
        ...AvatarCardPopover.props,
        model: { type: String, optional: true },
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
        this.store = useService("mail.store");
        this.openChat = useOpenChat("res.users");
        onWillStart(this.onWillStart);
        onWillUnmount(() => {
            if (this.partner?.stopRealtimeTzDiff) {
                this.partner.stopRealtimeTzDiff();
                this.partner.stopRealtimeTzDiff = null;
            }
        });
    }

    async onWillStart() {
        [this.record] = await this.orm.call(this.props.recordModel, 'get_avatar_card_data', [[this.props.id], this.fieldNames], {});
        const userId = this.record.user_id[0];
        this.store.fetchStoreData("avatar_card", {
            id: userId,
            model: "res.users",
        });
        await Promise.all(this.loadAdditionalData());
    }

    loadAdditionalData() {
        // To use when overriden in other modules to load additional data, returns promise(s)
        return [];
    }

    get fieldNames() {
        return ["email", "im_status", "name", "phone", "resource_type", "share", "user_id"];
    }

    get partner() {
        const userId = this.record.user_id[0];
        const user = this.store["res.users"].get(userId);
        return user?.partner_id;
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

    onSendClick() {
        this.openChat(this.userId);
        this.props.close();
    }
}
