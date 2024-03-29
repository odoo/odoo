/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onWillUpdateProps, onWillStart, useState, onWillRender } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ChannelMemberList extends Component {
    static components = { ImStatus, ActionPanel };
    static props = ["thread", "openChannelInvitePanel", "className?"];
    static template = "discuss.ChannelMemberList";

    setup() {
        this.store = useState(useService("mail.store"));
        this.channelMemberService = useService("discuss.channel.member");
        this.threadService = useState(useService("mail.thread"));
        onWillStart(() => {
            if (this.props.thread.fetchMembersState === "not_fetched") {
                this.threadService.fetchChannelMembers(this.props.thread);
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.fetchMembersState === "not_fetched") {
                this.threadService.fetchChannelMembers(nextProps.thread);
            }
        });
        onWillRender(() => {
            this.onlineMembers = this.props.thread.onlineMembers;
            this.offlineMembers = this.props.thread.offlineMembers;
        });
    }

    canOpenChatWith(member) {
        if (this.store.inPublicPage) {
            return false;
        }
        if (member.persona?.eq(this.store.self)) {
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

    get title() {
        return _t("Member List");
    }
}
