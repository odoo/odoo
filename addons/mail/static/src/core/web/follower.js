import { useService } from "@web/core/utils/hooks";
import { Component, t, useProps } from "@odoo/owl";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { propComputed } from "@mail/utils/common/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";
import { onFollowerChangedType } from "@mail/core/web/follower_types";

export class Follower extends Component {
    static template = "mail.Follower";
    static components = { DropdownItem };

    setup() {
        this.store = useService("mail.store");
        this.close = useProps.static("close", t.function([]).optional());
        this.follower = propComputed("follower", t.instanceOf(this.store["mail.followers"]));
        this.onFollowerChanged = useProps.static(
            "onFollowerChanged",
            onFollowerChangedType(this.store).optional()
        );
        this.avatarCard = usePopover(AvatarCard, { position: "right" });
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ followerAtRender: import("models").Follower }} param1
     */
    onClickDetails(ev, { followerAtRender }) {
        if (this.avatarCard.isOpen) {
            return;
        }
        this.avatarCard.open(ev.currentTarget, {
            id: followerAtRender.partner_id.id,
            model: "res.partner",
        });
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ followerAtRender: import("models").Follower }} param1
     */
    async onClickEdit(ev, { followerAtRender }) {
        this.env.services.dialog.add(FollowerSubtypeDialog, {
            follower: followerAtRender,
            /** @type {ReturnType<typeof onFollowerChangedType>["type"]} */
            onFollowerChanged: ({ thread }) => this.onFollowerChanged?.({ thread }),
        });
        this.close?.();
    }

    /**
     * @param {MouseEvent} ev
     * @param {{ followerAtRender: import("models").Follower }} param1
     */
    async onClickRemove(ev, { followerAtRender }) {
        const thread = followerAtRender.thread;
        await followerAtRender.remove();
        this.onFollowerChanged?.({ thread });
    }
}
