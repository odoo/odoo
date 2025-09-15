import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { ImStatus } from "@mail/core/common/im_status";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";
    static components = { ImStatus };
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
        this.store = useService("mail.store");
        this.openChat = useOpenChat(this.props.model);
        this.store.fetchStoreData("avatar_card", {
            id: this.props.id,
            model: this.props.model,
        });
    }

    get user() {
        if (this.props.model === "res.users") {
            return this.store["res.users"].get(this.props.id);
        }
        return undefined;
    }

    get partner() {
        if (this.props.model === "res.partner") {
            return this.store["res.partner"].get(this.props.id);
        }
        return this.user?.partner_id;
    }

    get name() {
        return this.partner?.name;
    }

    get email() {
        return this.partner?.email;
    }

    get phone() {
        return this.partner?.phone;
    }

    get showViewProfileBtn() {
        return this.partner;
    }

    get hasFooter() {
        return false;
    }

    async getProfileAction() {
        return {
            res_id: this.partner.id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }

    onSendClick() {
        this.openChat(this.props.id);
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
