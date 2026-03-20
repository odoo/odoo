import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

export class AvatarCardResourcePopover extends AvatarCardPopover {
    static template = "resource_mail.AvatarCardResourcePopover";

    static props = {
        ...AvatarCardPopover.props,
        model: { type: String, optional: true },
    };

    static defaultProps = {
        ...AvatarCardPopover.defaultProps,
        model: "resource.resource",
    };

    get openChatModel() {
        return "res.users";
    }

    get resource() {
        return this.store["resource.resource"].get(this.props.id);
    }

    get user() {
        return this.resource?.user_id;
    }

    get name() {
        return this.resource?.name;
    }

    get displayAvatar() {
        return this.resource?.resource_type !== "material";
    }

    get showViewProfileBtn() {
        return false;
    }

    onSendClick() {
        this.openChat(this.user.id);
        this.props.close();
    }
}
