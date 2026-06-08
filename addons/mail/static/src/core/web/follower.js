import { useService } from "@web/core/utils/hooks";
import { Component, props, types } from "@odoo/owl";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";

export class Follower extends Component {
    static template = "mail.Follower";
    static components = { DropdownItem };

    setup() {
        this.store = useService("mail.store");
        this.props = props({
            close: types.function([]).optional(),
            follower: types.instanceOf(this.store["mail.followers"].Class),
            onFollowerChanged: types.function([]).optional(),
        });
        this.avatarCard = usePopover(AvatarCard, { position: "right" });
    }

    onClickDetails(ev) {
        if (this.avatarCard.isOpen) {
            return;
        }
        this.avatarCard.open(ev.currentTarget, {
            id: this.props.follower.partner_id.id,
            model: "res.partner",
        });
    }

    async onClickEdit() {
        this.env.services.dialog.add(FollowerSubtypeDialog, {
            follower: this.props.follower,
            onFollowerChanged: (thread) => this.props.onFollowerChanged?.(thread),
        });
        this.props.close?.();
    }

    async onClickRemove() {
        const thread = this.props.follower.thread;
        await this.props.follower.remove();
        this.props.onFollowerChanged?.(thread);
    }
}
