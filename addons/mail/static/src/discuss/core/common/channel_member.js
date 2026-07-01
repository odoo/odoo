import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { useChannelMemberActions } from "@mail/discuss/core/common/channel_member_actions";
import { propComputed } from "@mail/utils/common/hooks";

import { Component, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

import { useService } from "@web/core/utils/hooks";
import { ActionList } from "@mail/core/common/action_list";

export class ChannelMember extends Component {
    static components = { ActionList, ActionPanel, DiscussAvatar, Dropdown };
    static template = "discuss.ChannelMember";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.member = propComputed(
            "member",
            t.instanceOf(this.store["discuss.channel.member"].Class)
        );
        this.actions = useChannelMemberActions({ member: this.member });
        this.showingActions = useDropdownState();
    }

    /** @param {import("models").ChannelMember} member */
    isClickable(member) {
        return this.canOpenChat(member);
    }

    get attClass() {
        return {
            "cursor-pointer": this.isClickable(this.member()),
            "o-offline": this.member().imStatusUI === "offline",
        };
    }

    /** @param {import("models").ChannelMember} member */
    canOpenChat(member) {
        if (this.store.inPublicPage) {
            return false;
        }
        if (member.partner_id?.main_user_id) {
            return true;
        }
        return false;
    }

    /**
     * @param {MouseEvent} ev
     * @param {Object} param1
     * @param {import("models").ChannelMember} param1.memberAtRender
     */
    onClickAvatar(ev, { memberAtRender }) {
        if (!this.isClickable(memberAtRender)) {
            return;
        }
        this.store.openChat({ partnerId: memberAtRender.partner_id.id });
    }
}
