import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";

export class AvatarPartnerCardPopover extends Component {
    static template = "calendar.AvatarPartnerCardPopover";

    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.openChat = useOpenChat("res.partner");
        onWillStart(async () => {
            [this.partner] = await this.orm.read("res.partner", [this.props.id], this.fieldNames);
        });
    }

    get fieldNames() {
        return ["name", "email", "phone", "im_status"];
    }

    get email() {
        return this.partner.email;
    }

    get phone() {
        return this.partner.phone;
    }

    get showViewProfileBtn() {
        return true;
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

    get partnerId() {
        return this.partner.id;
    }

    onSendClick() {
        this.openChat(this.partner.id);
        this.props.close();
    }

    async onClickViewProfile(newWindow) {
        const action = await this.getProfileAction();
        this.actionService.doAction(action, { newWindow });
    }
}
