import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";
    static components = { Dropdown, DropdownItem };
    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
        thread: { type: Object, optional: true },
        channelMember: { type: Object, optional: true },
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.dialog = useService("dialog");
        this.openChat = useOpenChat("res.users");
        onWillStart(async () => {
            [this.user] = await this.orm.read("res.users", [this.props.id], this.fieldNames);
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
            res_id: this.user.partner_id[0],
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
    onClickRemove() {
        this.dialog.add(ConfirmationDialog, {
            body: _t(
                'Do you want to remove "%s" from this channel?',
                this.props.channelMember?.persona.name
            ),
            cancel: () => {},
            confirm: () => this.props.channelMember?.removeFromChannel(),
        });
        this.props.close();
    }
    onClickToggleAdmin(setAdmin) {
        this.props.channelMember?.setChannelRole(setAdmin ? "admin" : false);
        this.props.close();
    }
    onClickTransferOwnership() {
        this.dialog.add(ConfirmationDialog, {
            body: _t(
                'Do you want to transfer ownership to "%s"? This means that the member will have full control over the channel and its settings.\n\nThis action cannot be reverted.',
                this.props.channelMember?.persona.name
            ),
            cancel: () => {},
            confirm: () => this.props.channelMember?.transferOwnership(),
        });
        this.props.close();
    }
    async onClickViewProfile(newWindow) {
        const action = await this.getProfileAction();
        this.actionService.doAction(action, { newWindow });
    }
}
