import { NotificationItem } from "@mail/core/public_web/notification_item";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { SubChannelPreview } from "@mail/discuss/core/public_web/sub_channel_preview";
import { useSearch, useVisible } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class SubChannelList extends Component {
    static template = "mail.SubChannelList";
    static components = { ActionPanel, NotificationItem, SubChannelPreview };

    static props = ["channel", "close?"];

    setup() {
        this.store = useService("mail.store");
        this.search = useSearch({
            initialResults: this.props.channel.sub_channel_ids,
            fetch: (term) => this.props.channel.loadMoreSubChannels({ searchTerm: term }),
            filter: (term) =>
                fuzzyLookup(term, this.props.channel.sub_channel_ids, ({ name }) => name),
        });
        useAutofocus({ refName: "search" });
        this.loadMoreState = useVisible("load-more", (isVisible) => {
            if (isVisible) {
                this.props.channel.loadMoreSubChannels({
                    searchTerm: this.search.searchTerm || undefined,
                });
            }
        });
    }

    /**
     * @param {import("models").DiscussChannel} subChannel
     */
    async onClickSubChannel(subChannel) {
        subChannel.open({ focus: true });
        this.props.close?.();
    }

    async onClickCreate() {
        await this.props.channel.createSubChannel({ name: this.search.searchTerm });
        this.search.run({ skipFetch: true });
        this.props.close?.();
    }
}
