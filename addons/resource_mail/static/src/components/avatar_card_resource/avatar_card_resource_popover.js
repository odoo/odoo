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
        return super.displayAvatar && this.user;
    }

    get showViewProfileBtn() {
        return false;
    }
}
