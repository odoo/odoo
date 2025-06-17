import { ImStatus } from "@mail/core/common/im_status";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import { useService } from "@web/core/utils/hooks";

export class ChannelMemberList extends Component {
    static components = { ImStatus, ActionPanel };
    static props = ["thread", "openChannelInvitePanel", "className?"];
    static template = "discuss.ChannelMemberList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
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

    get onlineSectionText() {
        return _t("Online - %(online_count)s", {
            online_count: this.props.thread.onlineMembers.length,
        });
    }

    get offlineSectionText() {
        return _t("Offline - %(offline_count)s", {
            offline_count: this.props.thread.offlineMembers.length,
        });
    }

    canOpenChatWith(member) {
        if (this.store.inPublicPage) {
            return false;
        }
        if (member.guest_id) {
            return false;
        }
        return true;
    }

    onClickAvatar(ev, member) {
        if (!this.canOpenChatWith(member)) {
            return;
        }
        this.store.openChat({ partnerId: member.partner_id.id });
    }
}
