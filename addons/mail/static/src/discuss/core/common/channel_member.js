import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { useChannelMemberActions } from "@mail/discuss/core/common/channel_member_actions";

import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

import { useService } from "@web/core/utils/hooks";
import { ActionList } from "@mail/core/common/action_list";

export class ChannelMember extends Component {
    static components = { ActionList, ActionPanel, DiscussAvatar, Dropdown };
    static props = ["member"];
    static template = "discuss.ChannelMember";

    setup() {
        super.setup();
        this.state = useState({});
        this.store = useService("mail.store");
        this.actions = useChannelMemberActions({ member: () => this.props.member });
        this.showingActions = useDropdownState();
    }

    /** @return {import("models").ChannelMember} */
    get member() {
        return this.props.member;
    }

    get attClass() {
        return { "cursor-pointer": this.canOpenChat, "o-offline": !this.member.isOnline };
    }

    get canOpenChat() {
        if (this.store.inPublicPage) {
            return false;
        }
        if (this.member.partner_id) {
            return true;
        }
        return false;
    }

    onClickAvatar(ev) {
        if (!this.canOpenChat) {
            return;
        }
        this.store.openChat({ partnerId: this.member.partner_id.id });
    }
}
