import { useService } from "@web/core/utils/hooks";
import { Component, signal, types, useProps } from "@odoo/owl";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { usePopover } from "@web/core/popover/popover_hook";

export class Follower extends Component {
    static template = "mail.Follower";

    isEditing = signal(false);

    setup() {
        this.store = useService("mail.store");
        this.props = useProps({
            follower: types.instanceOf(this.store["mail.followers"]),
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

    onClickEdit() {
        this.isEditing.set(true);
        this.env.services.dialog.add(
            FollowerSubtypeDialog,
            {
                follower: this.props.follower,
                onFollowerChanged: (thread) => this.props.onFollowerChanged?.(thread),
            },
            { onClose: () => this.isEditing.set(false) }
        );
    }

    async onClickRemove() {
        const thread = this.props.follower.thread;
        await this.props.follower.remove();
        this.props.onFollowerChanged?.(thread);
    }
}
