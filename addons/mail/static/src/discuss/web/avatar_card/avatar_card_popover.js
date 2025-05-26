import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";

    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
    };

    setup() {
        this.actionService = useService("action");
        this.store = useService("mail.store");
        this.openChat = useOpenChat("res.users");
        this.store.fetchStoreData("avatar_card", { user_id: this.props.id });
    }

    get user() {
        return this.store["res.users"].get(this.props.id);
    }

    get name() {
        return this.user?.name;
    }

    get email() {
        return this.user?.email;
    }

    get phone() {
        return this.user?.phone;
    }

    get showViewProfileBtn() {
        return this.user;
    }

    get hasFooter() {
        return false;
    }

    async getProfileAction() {
        if (!this.user?.partner_id) {
            return this.user?.partner_id;
        }
        return {
            res_id: this.user.partner_id,
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
