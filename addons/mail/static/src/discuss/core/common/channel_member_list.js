import { ImStatus } from "@mail/core/common/im_status";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onWillUpdateProps, onWillStart, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ChannelMemberList extends Component {
    static components = { ImStatus, ActionPanel };
    static props = ["thread", "openChannelInvitePanel", "className?"];
    static template = "discuss.ChannelMemberList";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        onWillStart(() => {
            if (this.props.thread.fetchMembersState === "not_fetched") {
                this.props.thread.fetchChannelMembers();
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.thread.fetchMembersState === "not_fetched") {
                nextProps.thread.fetchChannelMembers();
            }
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
        this.store.openChat({ partnerId: member.persona.id });
    }

    get title() {
        return _t("Member List");
    }
}
