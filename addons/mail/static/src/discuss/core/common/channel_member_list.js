import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { ChannelActionDialog } from "@mail/discuss/core/common/channel_action_dialog";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";

import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@web/owl2/utils";

import { useService } from "@web/core/utils/hooks";
import { useSequential } from "@mail/utils/common/hooks";

let nextId = 0;

/**
 * @typedef {Object} Props
 * @property {import("models").DiscussChannel} channel
 * @property {string} [className]
 * @property {Function} [openChannelInvitePanel]
 * @property {Function} [close]
 * @extends {Component<Props, Env>}
 */
export class ChannelMemberList extends Component {
    static components = { ActionPanel, ChannelActionDialog, ChannelMember };
    static props = ["channel", "close?", "openChannelInvitePanel", "className?"];
    static template = "discuss.ChannelMemberList";

    setup() {
        super.setup();
        this.uniqueId = `discuss.ChannelMemberList.${nextId++}`;
        this.store = useService("mail.store");
        this.dialogService = useService("dialog");
        this.state = useState({ searchTerm: "", isSearching: false });
        this.lastFetchedSearch = undefined;
        this.sequential = useSequential();
        onWillStart(() => {
            if (this.props.channel.fetchMembersState === "not_fetched") {
                this.props.channel.fetchChannelMembers();
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.channel.fetchMembersState === "not_fetched") {
                nextProps.channel.fetchChannelMembers();
            }
            if (nextProps.channel.notEq(this.props.channel) && this.state.searchTerm) {
                this.state.searchTerm = "";
                this.state.isSearching = false;
            }
            if (nextProps.channel.notEq(this.props.channel)) {
                this.lastFetchedSearch = undefined;
            }
        });
    }

    /* @param {import("models").ChannelMember[]} members */
    _getFilteredByTerm(members) {
        if (!this.state.searchTerm) {
            return members;
        }
        const term = this.state.searchTerm.toLowerCase();
        return members.filter((m) => m.name?.toLowerCase().includes(term));
    }

    get matchingOnlineMembers() {
        return this._getFilteredByTerm(this.props.channel.onlineMembers);
    }

    get matchingOfflineMembers() {
        return this._getFilteredByTerm(this.props.channel.offlineMembers);
    }

    get matchingUnknownStatusMembers() {
        return this._getFilteredByTerm(this.props.channel.unknownStatusMembers);
    }

    get filteredOnlineMembers() {
        if (!this.state.searchTerm) {
            return this.matchingOnlineMembers;
        }
        return this.matchingOnlineMembers.slice(0, 100);
    }

    get filteredOfflineMembers() {
        if (!this.state.searchTerm) {
            return this.matchingOfflineMembers;
        }
        const remaining = 100 - this.filteredOnlineMembers.length;
        return this.matchingOfflineMembers.slice(0, Math.max(0, remaining));
    }

    get filteredUnknownStatusMembers() {
        if (!this.state.searchTerm) {
            return this.matchingUnknownStatusMembers;
        }
        const remaining =
            100 - this.filteredOnlineMembers.length - this.filteredOfflineMembers.length;
        return this.matchingUnknownStatusMembers.slice(0, Math.max(0, remaining));
    }

    get onlineSectionText() {
        return _t("Online - %(online_count)s", {
            online_count: this.filteredOnlineMembers.length,
        });
    }

    get offlineSectionText() {
        return _t("Offline - %(offline_count)s", {
            offline_count: this.filteredOfflineMembers.length,
        });
    }

    get unknownStatusSectionText() {
        return _t("Others - %(unknown_status_count)s", {
            unknown_status_count: this.filteredUnknownStatusMembers.length,
        });
    }

    get isSearchResultCapped() {
        if (!this.state.searchTerm) {
            return false;
        }
        return (
            this.matchingOnlineMembers.length +
                this.matchingOfflineMembers.length +
                this.matchingUnknownStatusMembers.length >=
            100
        );
    }

    get hasFilteredMembers() {
        return (
            this.filteredOnlineMembers.length > 0 ||
            this.filteredOfflineMembers.length > 0 ||
            this.filteredUnknownStatusMembers.length > 0
        );
    }

    get filteredMembersCount() {
        return (
            this.filteredOnlineMembers.length +
            this.filteredOfflineMembers.length +
            this.filteredUnknownStatusMembers.length
        );
    }

    isSearchMoreSpecificThanLastFetch(searchTerm) {
        return (
            this.lastFetchedSearch?.channelId === this.props.channel.id &&
            searchTerm.startsWith(this.lastFetchedSearch.searchTerm)
        );
    }

    get searchResultCapHint() {
        return _t("Showing first 100 members. Narrow your search to see more.");
    }

    /** @param {KeyboardEvent} ev */
    onInputSearch(ev) {
        const searchTerm = ev.target.value;
        this.state.searchTerm = searchTerm;
        if (!searchTerm) {
            this.lastFetchedSearch = undefined;
            this.state.isSearching = false;
            return;
        }
        if (
            this.lastFetchedSearch?.count === 0 &&
            this.isSearchMoreSpecificThanLastFetch(searchTerm)
        ) {
            this.state.isSearching = false;
            return;
        }
        this.state.isSearching = true;
        this.sequential(async () => {
            try {
                await this.props.channel.searchChannelMembers(searchTerm);
                if (this.state.searchTerm === searchTerm) {
                    this.lastFetchedSearch = {
                        channelId: this.props.channel.id,
                        searchTerm,
                        count: this.filteredMembersCount,
                    };
                }
            } finally {
                if (this.state.searchTerm === searchTerm) {
                    this.state.isSearching = false;
                }
            }
        });
    }

    onClickInviteButton() {
        if (this.env.inMeetingView) {
            this.props.openChannelInvitePanel?.({ keepPrevious: true });
        } else {
            this.dialogService.add(ChannelActionDialog, {
                contentClass: "o-discuss-ChannelInvitation",
                contentComponent: ChannelInvitation,
                contentProps: {
                    channel: this.props.channel,
                    close: () => this.store.env.services.dialog.closeAll(),
                },
                title: this.props.channel.displayName,
            });
        }
    }
}
