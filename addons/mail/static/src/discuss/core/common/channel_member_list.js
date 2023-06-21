/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";

import { Component, onWillUpdateProps, onWillStart, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class ChannelMemberList extends Component {
    static components = { ImStatus };
    static props = ["thread", "className?"];
    static template = "discuss.ChannelMemberList";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.channelMemberService = useService("discuss.channel.member");
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
        if (member.persona.type === "guest") {
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
