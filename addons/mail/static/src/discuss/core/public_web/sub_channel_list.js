import { RelativeTime } from "@mail/core/common/relative_time";
import { NotificationItem } from "@mail/core/public_web/notification_item";
import { useVisible } from "@mail/utils/common/hooks";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { ActionPanel } from "../common/action_panel";
import { fuzzyLookup } from "@web/core/utils/search";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class SubChannelList extends Component {
    static template = "mail.SubChannelList";
    static components = { ActionPanel, RelativeTime, NotificationItem };

    static props = ["thread", "close"];

    setup() {
        this.store = useService("mail.store");
        this.state = useState({
            loading: false,
            searchTerm: "",
            searching: false,
            subChannels: this.props.thread.sub_channel_ids,
        });
        this.searchRef = useRef("search");
        useAutofocus({ refName: "search" });
        useVisible("load-more", async (isVisible) => {
            if (isVisible) {
                await this.props.thread.loadMoreSubChannels({
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

    onClickCreate() {
        this.props.thread.createSubChannel();
    }

    async onClickSubThread(subThread) {
        if (!subThread.hasSelfAsMember) {
            await rpc("/mail/channel/sub_channel/join", { sub_channel_id: subThread.id });
        }
        subThread.open();
    }

    clearSearch() {
        this.state.searchTerm = undefined;
        this.state.searching = false;
        this.state.loading = false;
        this.state.subChannels = this.props.thread.sub_channel_ids;
    }

    onKeydownSearch(ev) {
        if (ev.key !== "Enter") {
            return;
        }
        this.search();
    }

    async search() {
        if (!this.state.searchTerm) {
            this.clearSearch();
            return;
        }
        this.state.searching = true;
        this.state.loading = true;
        try {
            await this.props.thread.loadMoreSubChannels({
                searchTerm: this.state.searchTerm,
            });
            if (this.state.searching) {
                this.state.subChannels = fuzzyLookup(
                    this.state.searchTerm,
                    this.props.thread.sub_channel_ids,
                    ({ name }) => name
                );
            }
        } finally {
            this.state.loading = false;
        }
    }
}
