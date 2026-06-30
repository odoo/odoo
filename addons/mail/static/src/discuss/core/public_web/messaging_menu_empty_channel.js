import { MessagingMenuEmpty } from "@mail/core/public_web/messaging_menu/messaging_menu_empty";

import { Component, props, types, untrack, useEffect } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class MessagingMenuEmptyChannel extends Component {
    static template = "mail.MessagingMenuEmptyChannel";
    static components = { MessagingMenuEmpty };

    setup() {
        super.setup(...arguments);
        this.props = props({ title: types.string(), subtitle: types.string().optional() });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        useEffect(() => {
            untrack(() => this.store.fetchMostPopularChannelsFetcher.fetch());
        });
    }

    onClickFollow(channel) {
        if (channel.self_member_id) {
            channel.pinRpc();
            return;
        }
        const params = { channel_id: channel.id };
        if (this.store.self_user) {
            params.user_ids = [this.store.self_user.id];
        } else {
            params.guest_ids = [this.store.self_guest.id];
        }
        this.store.fetchStoreData("/discuss/channel/add_members", params);
    }
}
