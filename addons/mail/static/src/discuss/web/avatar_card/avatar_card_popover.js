import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";

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
        this.store = useService("mail.store");
        this.openChat = useOpenChat("res.users");
        this.store.fetchStoreData("avatar_card", {
            id: this.props.id,
            res_model: this.props.resModel,
        });
    }

    get partner() {
        if (this.props.resModel === "res.partner") {
            return this.store["res.partner"].get(this.props.id);
        }
        return null;
    }

    get user() {
        if (this.partner) {
            return this.partner.user_id ? this.store["res.users"].get(this.partner.user_id) : null;
        }
        return this.store[this.props.resModel].get(this.props.id);
    }

    get name() {
        return this.user?.name || this.partner?.name;
    }

    get email() {
        return this.user?.email || this.partner?.email;
    }

    get phone() {
        return this.user?.phone || this.partner?.phone;
    }

    get showViewProfileBtn() {
        return this.user || this.partner;
    }

    get hasFooter() {
        return false;
    }

    async getProfileAction() {
        if (!this.user?.partner_id && !this.partner?.id) {
            return false;
        }
        return {
            res_id: this.user?.partner_id || this.partner.id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }

    get userId() {
        return this.user?.id;
    }

    onSendClick() {
        this.openChat(this.userId);
        this.props.close();
    }

    async onClickViewProfile(newWindow) {
        const action = await this.getProfileAction();
        if (!action) {
            return;
        }
        this.actionService.doAction(action, { newWindow });
    }
}
