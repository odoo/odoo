import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { ChannelMember } from "@mail/discuss/core/common/channel_member";

import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import { useService } from "@web/core/utils/hooks";

export class ChannelMemberList extends Component {
    static components = { ActionPanel, ChannelMember };
    static props = ["channel", "openChannelInvitePanel", "className?"];
    static template = "discuss.ChannelMemberList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        onWillStart(() => {
            if (this.props.channel.fetchMembersState === "not_fetched") {
                this.props.channel.fetchChannelMembers();
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.channel.fetchMembersState === "not_fetched") {
                nextProps.channel.fetchChannelMembers();
            }
        });
    }

    get onlineSectionText() {
        return _t("Online - %(online_count)s", {
            online_count: this.props.channel.onlineMembers.length,
        });
    }

    get offlineSectionText() {
        return _t("Offline - %(offline_count)s", {
            offline_count: this.props.channel.offlineMembers.length,
        });
    }
}
