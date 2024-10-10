import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
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
        this.orm = useService("orm");
        this.openChat = useOpenChat("res.users");
        onWillStart(async () => {
            const modelName = this.props.resModel === "res.users" ? "res.users" : "res.partner";
            [this.avatarEntity] = await this.orm.read(
                modelName,
                [this.props.id],
                this.fieldNames[this.props.resModel === "res.users" ? "users" : "partners"]
            );
        });
    }

    get fieldNames() {
        return {
            users: ["name", "email", "phone", "im_status", "share", "partner_id"],
            partners: ["name", "email", "phone", "im_status", "partner_share"],
        };
    }

    get email() {
        return this.avatarEntity.email;
    }

    get phone() {
        return this.avatarEntity.phone;
    }

    get userShare() {
        if (this.props.resModel === "res.users") {
            return this.avatarEntity.share;
        } else {
            return this.avatarEntity.partner_share;
        }
    }

    get showViewProfileBtn() {
        return true;
    }

    async getProfileAction() {
        const id =
            this.props.resModel === "res.partner"
                ? this.avatarEntity.id
                : this.avatarEntity.partner_id[0];

        return {
            res_id: id,
            res_model: "res.partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    }

    get userId() {
        return this.avatarEntity.id;
    }

    onSendClick() {
        this.openChat(this.userId);
        this.props.close();
    }

    async onClickViewProfile() {
        const action = await this.getProfileAction();
        this.actionService.doAction(action);
    }
}
