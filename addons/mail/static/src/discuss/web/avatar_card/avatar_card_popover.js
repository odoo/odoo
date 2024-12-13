import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";

    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
        res_model: { type: String, optional: true },
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.openChat = useOpenChat("res.users");
        onWillStart(async () => {
            [this.user] = await this.orm.read(
                this.props.res_model,
                [this.props.id],
                this.fieldNames
            );
        });
    }

    static defaultProps = { res_model: "res.users" };

    get fieldNames() {
        if (this.props.res_model == "res.partner") {
            return ["name", "email", "phone", "im_status"];
        }
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

    async getProfileAction() {
        return {
            res_id: this.props.res_model == "res.users" ? this.user.partner_id[0] : this.user.id,
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
