import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { rpc } from "@web/core/network/rpc";
import { Component } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { ImStatus } from "@mail/core/common/im_status";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";
    static components = { Dropdown, DropdownItem, ImStatus };
    static props = {
        id: { type: Number, required: true },
        channelMember: { type: Object, optional: true },
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
        this.dialog = useService("dialog");
        this.openChat = useOpenChat(this.openChatModel);
        this.store.fetchStoreData("avatar_card", {
            id: this.props.id,
            model: this.props.model,
        });
    }

    get openChatModel() {
        return this.props.model;
    }

    get canOpenSettingMenu() {
        return (
            this.canSetAdmin ||
            this.canRemoveAdmin ||
            this.canSetOwner ||
            this.canRemoveOwner ||
            this.canRemoveMember
        );
    }

    get selfChannelRole() {
        return this.props.channelMember?.channel_id?.self_member_id?.channel_role;
    }

    get currentChannelRole() {
        return this.props.channelMember?.channel_role;
    }

    get canSetAdmin() {
        return (
            this.props.channelMember &&
            this.currentChannelRole !== "admin" &&
            (this.store.self_user?.is_admin ||
                (this.selfChannelRole === "owner" && this.currentChannelRole !== "owner") ||
                (this.selfChannelRole === "owner" && this.props.channelMember?.threadAsSelf))
        );
    }

    get canRemoveAdmin() {
        return (
            this.props.channelMember &&
            this.currentChannelRole === "admin" &&
            (this.store.self_user?.is_admin || this.selfChannelRole === "owner")
        );
    }

    get canSetOwner() {
        return (
            this.props.channelMember &&
            this.currentChannelRole !== "owner" &&
            (this.store.self_user?.is_admin || this.selfChannelRole === "owner")
        );
    }

    get canRemoveOwner() {
        return (
            this.props.channelMember &&
            this.currentChannelRole === "owner" &&
            (this.store.self_user?.is_admin || this.props.channelMember?.threadAsSelf)
        );
    }

    get canRemoveMember() {
        return (
            this.props.channelMember &&
            (this.store.self_user?.is_admin ||
                (this.selfChannelRole && this.currentChannelRole !== "owner"))
        );
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

    onClickRemove() {
        this.dialog.add(ConfirmationDialog, {
            body: _t('Do you want to remove "%(member_name)s" from this channel?', {
                member_name: this.props.channelMember.name,
            }),
            cancel: () => {},
            confirm: () => {
                rpc("/discuss/channel/remove_member", {
                    member_id: this.props.channelMember.id,
                });
                this.props.close();
            },
        });
    }

    setChannelRole(role) {
        if (
            !this.store.self_user?.is_admin &&
            (this.props.channelMember.threadAsSelf || role === "owner")
        ) {
            this.dialog.add(ConfirmationDialog, {
                body: this.props.channelMember.threadAsSelf
                    ? _t(
                          "Do you want to remove owner from yourself? You will no longer have full control over the channel and its settings."
                      )
                    : _t(
                          'Do you want to set "%(member_name)s" as the owner? This means that the member will have full control over the channel and its settings.\n\nThis action cannot be reverted.',
                          { member_name: this.props.channelMember.name }
                      ),
                cancel: () => {},
                confirm: () => this.props.channelMember.setChannelRole(role),
            });
        } else {
            this.props.channelMember.setChannelRole(role);
        }
    }

    async onClickViewProfile(newWindow) {
        const action = await this.getProfileAction();
        if (!action) {
            return;
        }
        this.actionService.doAction(action, { newWindow });
    }
}
