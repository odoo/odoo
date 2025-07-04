import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";
import { useService } from "@web/core/utils/hooks";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { onWillStart } from "@odoo/owl";

export class AvatarPartnerCardPopover extends AvatarCardPopover {
    static template = "calendar.AvatarPartnerCardPopover";

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.openChat = useOpenChat("res.partner");
        onWillStart(async () => {
            [this.user] = await this.orm.read("res.partner", [this.props.id], this.fieldNames);
        });
    }

    get fieldNames() {
        return ["name", "email", "phone", "im_status"];
    }

    async getProfileAction() {
        return {
            res_id: this.user.id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }
}
