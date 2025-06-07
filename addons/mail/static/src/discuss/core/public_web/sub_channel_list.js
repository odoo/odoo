import { NotificationItem } from "@mail/core/public_web/notification_item";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { isToday } from "@mail/utils/common/dates";
import { useSequential, useVisible } from "@mail/utils/common/hooks";
import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";

const { DateTime } = luxon;

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/common/thread_model").Thread} thread
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class SubChannelList extends Component {
    static template = "mail.SubChannelList";
    static components = { ActionPanel, NotificationItem };

    static props = ["thread", "close?"];

    setup() {
        this.store = useService("mail.store");
        this.state = useState({
            loading: false,
            searchTerm: "",
            lastSearchTerm: "",
            searching: false,
            subChannels: this.props.thread.sub_channel_ids,
        });
        this.searchRef = useRef("search");
        this.sequential = useSequential();
        useAutofocus({ refName: "search" });
        useVisible("load-more", (isVisible) => {
            if (isVisible) {
                this.props.thread.loadMoreSubChannels({
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

    get NO_THREAD_FOUND() {
        return _t(`No thread named "%(thread_name)s"`, { thread_name: this.state.lastSearchTerm });
    }

    async onClickSubThread(subThread) {
        if (!subThread.hasSelfAsMember) {
            await rpc("/discuss/channel/join", { channel_id: subThread.id });
        }
        subThread.open();
        if (this.env.inChatWindow) {
            this.props.close?.();
        }
    }

    clearSearch() {
        this.state.searchTerm = "";
        this.state.lastSearchTerm = "";
        this.state.searching = false;
        this.state.loading = false;
        this.state.subChannels = this.props.thread.sub_channel_ids;
    }

    dateText(message) {
        if (isToday(message.datetime)) {
            return message.datetime?.toLocaleString(DateTime.TIME_SIMPLE);
        }
        return message.datetime?.toLocaleString(DateTime.DATE_MED);
    }

    onKeydownSearch(ev) {
        if (ev.key === "Enter") {
            this.search();
        }
    }

    async onClickCreate() {
        await this.props.thread.createSubChannel({ name: this.state.searchTerm });
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
                await this.props.thread.loadMoreSubChannels({
                    searchTerm: this.state.searchTerm,
                });
                if (this.state.searching) {
                    this._refreshSubChannelList();
                    this.state.lastSearchTerm = this.state.searchTerm;
                }
            } finally {
                this.state.loading = false;
            }
        });
    }

    _refreshSubChannelList() {
        this.state.subChannels = fuzzyLookup(
            this.state.searchTerm ?? "",
            this.props.thread.sub_channel_ids,
            ({ name }) => name
        );
    }
}
