/* @odoo-module */

import { Component, onWillUpdateProps, onWillStart, useState } from "@odoo/owl";
import { useMessaging, useStore } from "@mail/new/core/messaging_hook";
import { PartnerImStatus } from "./partner_im_status";
import { useService } from "@web/core/utils/hooks";

export class ChannelMemberList extends Component {
    static components = { PartnerImStatus };
    static props = ["thread", "className"];
    static template = "mail.channel_member_list";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.threadService = useState(useService("mail.thread"));
        onWillStart(() => this.threadService.fetchChannelMembers(this.props.thread));
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.channelMembers.length === 0) {
                this.threadService.fetchChannelMembers(nextProps.thread);
            }
        });
    }

    canOpenChatWith(member) {
        if (this.store.inPublicPage) {
            return false;
        }
        if (member.persona === this.store.self) {
            return false;
        }
        return true;
    }

    openChatAvatar(member) {
        if (!this.canOpenChatWith(member)) {
            return;
        }
        this.threadService.openChat({ partnerId: member.persona.id });
    }
}
