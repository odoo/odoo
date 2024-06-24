import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { rpc } from "@web/core/network/rpc";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";

    static props = {
        id: { type: Number, required: true },
        resModel: { type: String, optional: true },
        close: { type: Function, required: true },
    };

    static defaultProps = {
        resModel: "res.users",
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.openChat = useOpenChat("res.users");
        onWillStart(async () => {
            [this.user] = await rpc("/mail/avatar_card/info", {
                avatar_id: this.props.id,
                resModel: this.props.resModel,
                fieldNames: this.fieldNames,
            });
        });
    }

    get fieldNames() {
        return {
            partnerwithuser: ["name", "email", "phone", "im_status", "share", "partner_id"],
            partnerwithoutuser: ["name", "phone", "email", "im_status", "partner_share"],
        };
    }

    get email() {
        return this.user.email;
    }

    get phone() {
        return this.user.phone;
    }

    get userShare() {
        if (this.props.resModel === "res.users") {
            return this.user.share;
        } else {
            return this.user.partner_share;
        }
    }

    get showViewProfileBtn() {
        return true;
    }

    async getProfileAction() {
        const id = this.user.partner_id?.[0] ?? this.user.id;
        return {
            res_id: id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }

    onSendClick() {
        this.openChat(this.user.id);
    }

    async onClickViewProfile() {
        const action = await this.getProfileAction();
        this.actionService.doAction(action);
    }
}
