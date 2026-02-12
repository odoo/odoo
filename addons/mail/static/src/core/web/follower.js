import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";

/**
 * @typedef {Object} Props
 * @property {import("models").Follower} follower
 * @property {Function} [onFollowerChanged]
 * @property {Function} [close]
 * @extends {Component<Props, Env>}
 */
export class Follower extends Component {
    static template = "mail.Follower";
    static props = ["follower", "onFollowerChanged?", "close?"];
    static components = { DropdownItem };

    setup() {
        this.store = useService("mail.store");
        this.avatarCard = usePopover(AvatarCardPopover, { position: "right" });
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
            onFollowerChanged: () => this.props.onFollowerChanged?.(),
        });
        this.props.close?.();
    }

    async onClickRemove() {
        await this.props.follower.remove();
        this.props.onFollowerChanged?.();
    }
}
