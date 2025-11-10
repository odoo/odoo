import { ImStatus } from "@mail/core/common/im_status";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class ChannelMember extends Component {
    static components = { ImStatus, ActionPanel };
    static props = ["member"];
    static template = "discuss.ChannelMember";

    setup() {
        super.setup();
        this.store = useService("mail.store");
    }

    /** @return {import("models").ChannelMember} */
    get member() {
        return this.props.member;
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
