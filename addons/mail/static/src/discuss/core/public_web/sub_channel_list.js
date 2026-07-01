import { NotificationItem } from "@mail/core/public_web/notification_item";
import { SearchInput } from "@mail/core/common/search_input";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { SubChannelPreview } from "@mail/discuss/core/public_web/sub_channel_preview";
import { useSearch, useVisible } from "@mail/utils/common/hooks";
import { Component, props, types } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";

export class SubChannelList extends Component {
    static template = "mail.SubChannelList";
    static components = { ActionPanel, NotificationItem, SearchInput, SubChannelPreview };

    setup() {
        this.store = useService("mail.store");
        // bound once so `onClickSubChannel` is a stable (props.static) handler
        this.onClickSubChannel = this.onClickSubChannel.bind(this);
        this.props = props({
            channel: types.instanceOf(this.store["discuss.channel"].Class),
            close: types.function([types.instanceOf(MouseEvent)]).optional(),
        });
        this.search = useSearch({
            initialResults: this.props.channel.sub_channel_ids,
            fetch: (term) => this.props.channel.loadMoreSubChannels({ searchTerm: term }),
            filter: (term) =>
                fuzzyLookup(term, this.props.channel.sub_channel_ids, ({ name }) => name),
        });
        this.loadMoreState = useVisible("load-more", (isVisible) => {
            if (isVisible) {
                this.props.channel.loadMoreSubChannels({
                    searchTerm: this.search.searchTerm || undefined,
                });
            }
        });
    }

    /**
     * @type {ReturnType<typeof import("@mail/discuss/core/public_web/sub_channel_preview").subChannelPreviewOnClickType>["type"]}
     */
    async onClickSubChannel(ev, { channelAtRender }) {
        channelAtRender.open({ focus: true });
        this.props.close?.();
    }

    async onClickCreate() {
        await this.props.channel.createSubChannel({ name: this.search.searchTerm });
        this.search.run({ skipFetch: true });
        this.props.close?.();
    }
}
