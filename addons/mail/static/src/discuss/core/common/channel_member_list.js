/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";
import { avatarUrl, fetchChannelMembers, openChat } from "@mail/core/common/thread_service";

import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";

export class ChannelMemberList extends Component {
    static components = { ImStatus };
    static props = ["thread", "className?"];
    static template = "discuss.ChannelMemberList";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.avatarUrl = avatarUrl;
        this.fetchChannelMembers = fetchChannelMembers;
        onWillStart(() => fetchChannelMembers(this.props.thread));
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.channelMembers.length === 0) {
                fetchChannelMembers(nextProps.thread);
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
        openChat({ partnerId: member.persona.id });
    }
}
