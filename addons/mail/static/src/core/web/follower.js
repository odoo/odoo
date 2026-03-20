import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { FollowerSubtypeDialog } from "@mail/core/web/follower_subtype_dialog";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

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
    }

    onClickDetails() {
        this.store.openDocument({
            id: this.props.follower.partner_id.id,
            model: "res.partner"
        });
        this.props.close?.();
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
