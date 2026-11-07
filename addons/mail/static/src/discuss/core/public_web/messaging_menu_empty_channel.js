import { MessagingMenuEmpty } from "@mail/core/public_web/messaging_menu/messaging_menu_empty";

import { Component, types, untrack, useEffect, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenuEmptyChannel extends Component {
    static template = "mail.MessagingMenuEmptyChannel";
    static components = { MessagingMenuEmpty };

    setup() {
        super.setup(...arguments);
        this.props = useProps({ title: types.string(), subtitle: types.string().optional() });
        this.close = useProps.static("close", types.function().optional());
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useEffect(() => {
            untrack(() => this.store.fetchMostPopularChannelsFetcher.fetch());
        });
    }

    /** @param {import("models").DiscussChannel} channel */
    getFollowersText(channel) {
        if (channel.member_count === 1) {
            return _t("1 follower");
        }
        return _t("%(count)s followers", { count: channel.member_count });
    }

    onClickFindMoreChannels() {
        this.env.services.action.doAction("mail.discuss_channel_action");
        this.close?.();
    }

    /** @param {import("models").DiscussChannel} channel */
    onClickFollow(channel) {
        if (channel.self_member_id) {
            channel.pinRpc();
            return;
        }
        channel.joinRpc();
    }
}
