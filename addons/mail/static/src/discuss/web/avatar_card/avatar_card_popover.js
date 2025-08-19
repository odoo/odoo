import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { Component, onWillStart } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";

    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
        model: {
            type: String,
            validate: (m) => ["res.users", "res.partner"].includes(m),
            optional: true,
        },
    };
    static defaultProps = {
        model: "res.users",
    };

    setup() {
        this.actionService = useService("action");
        this.openChat = useOpenChat("res.users");
        onWillStart(async () => {
            this.user = await rpc("/discuss/avatar_card", {
                user_id: this.props.model === "res.users" ? this.props.id : false,
                partner_id: this.props.model === "res.partner" ? this.props.id : false,
                fields: this.fieldNames,
            });
            if (!this.user) {
                this.props.close();
            }
        });
    }

    get fieldNames() {
        return ["name", "email", "phone", "im_status", "share", "partner_id"];
    }

    get email() {
        return this.user.email;
    }

    get phone() {
        return this.user.phone;
    }

    get showViewProfileBtn() {
        return true;
    }

    get hasFooter() {
        return false;
    }

    async getProfileAction() {
        return {
            res_id: this.props.model === "res.partner" ? this.props.id : this.user.partner_id[0],
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }

    get userId() {
        return this.user.id;
    }

    onSendClick() {
        this.openChat(this.userId);
        this.props.close();
    }

    async onClickViewProfile(newWindow) {
        const action = await this.getProfileAction();
        this.actionService.doAction(action, { newWindow });
    }
}
