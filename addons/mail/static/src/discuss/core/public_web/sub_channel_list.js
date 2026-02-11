import { NotificationItem } from "@mail/core/public_web/notification_item";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { SubChannelPreview } from "@mail/discuss/core/public_web/sub_channel_preview";
import { useSequential, useVisible } from "@mail/utils/common/hooks";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
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
        this.state = useState({
            loading: false,
            searchTerm: "",
            searching: false,
            subChannels: this.props.channel.sub_channel_ids,
        });
        this.searchRef = useRef("search");
        this.sequential = useSequential();
        useAutofocus({ refName: "search" });
        this.loadMoreState = useVisible("load-more", (isVisible) => {
            if (isVisible) {
                this.props.channel.loadMoreSubChannels({
                    searchTerm: this.state.searching ? this.state.searchTerm : undefined,
                });
            }
        });
        useEffect(
            (searchTerm) => {
                if (!searchTerm) {
                    this.clearSearch();
                }
            },
            () => [this.state.searchTerm]
        );
    }

    /**
     * @param {import("models").DiscussChannel} subChannel
     */
    async onClickSubChannel(subChannel) {
        if (!subChannel.self_member_id) {
            await rpc("/discuss/channel/join", { channel_id: subChannel.id });
        }
        subChannel.open({ focus: true });
        this.props.close?.();
    }

    clearSearch() {
        this.state.searchTerm = "";
        this.state.searching = false;
        this.state.loading = false;
        this.state.subChannels = this.props.channel.sub_channel_ids;
    }

    onKeydownSearch(ev) {
        if (ev.key === "Enter") {
            this.search();
        }
    }

    async onClickCreate() {
        await this.props.channel.createSubChannel({ name: this.state.searchTerm });
        this._refreshSubChannelList();
        this.props.close?.();
    }

    async search() {
        if (!this.state.searchTerm) {
            return;
        }
        this.sequential(async () => {
            this.state.searching = true;
            this.state.loading = true;
            try {
                await this.props.channel.loadMoreSubChannels({
                    searchTerm: this.state.searchTerm,
                });
                if (this.state.searching) {
                    this._refreshSubChannelList();
                }
            } finally {
                this.state.loading = false;
            }
        });
    }

    _refreshSubChannelList() {
        this.state.subChannels = fuzzyLookup(
            this.state.searchTerm ?? "",
            this.props.channel.sub_channel_ids,
            ({ name }) => name
        );
    }
}
