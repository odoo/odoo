import { DiscussAvatar } from "@mail/core/common/discuss_avatar";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class ChannelMember extends Component {
    static components = { ActionPanel, DiscussAvatar };
    static props = ["member"];
    static template = "discuss.ChannelMember";

    setup() {
        super.setup();
        this.state = useState({});
        this.store = useService("mail.store");
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
