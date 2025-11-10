import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { ChannelMember } from "@mail/discuss/core/common/channel_member";

import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import { useService } from "@web/core/utils/hooks";

export class ChannelMemberList extends Component {
    static components = { ActionPanel, ChannelMember };
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
}
