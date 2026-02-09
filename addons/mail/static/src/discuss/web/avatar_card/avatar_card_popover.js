import { useState } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";
import { useOpenChat } from "@mail/core/web/open_chat_hook";
import { ImStatus } from "@mail/core/common/im_status";
import { useDynamicInterval } from "@mail/utils/common/misc";
import { formatLocalDateTime } from "@mail/utils/common/dates";
import { useChannelMemberActions } from "@mail/discuss/core/common/channel_member_actions";
import { ActionList } from "@mail/core/common/action_list";

export class AvatarCardPopover extends Component {
    static template = "mail.AvatarCardPopover";
    static components = { ActionList, Dropdown, DropdownItem, ImStatus };
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
        this.state = useState({ partnerLocalDateTimeFormatted: "" });
        this.store.fetchStoreData("avatar_card", {
            id: this.props.id,
            model: this.props.model,
        });
        this.chanelMemberActions = useChannelMemberActions({
            member: () => this.props.channelMember,
        });
        useDynamicInterval(
            (...args) => this.onChangeTz(...args),
            () => [this.partner?.tz, this.store.self?.tz]
        );
    }

    /**
     * @param {string} partnerTz
     * @param {string} currentUserTz
     */
    onChangeTz(partnerTz, currentUserTz) {
        this.state.partnerLocalDateTimeFormatted = formatLocalDateTime(partnerTz, currentUserTz);
        if (!this.state.partnerLocalDateTimeFormatted) {
            return;
        }
        return 60000 - (Date.now() % 60000);
    }

    get openChatModel() {
        return this.props.model;
    }

    get canOpenSettingMenu() {
        return this.props.channelMember && this.chanelMemberActions.actions.length;
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
