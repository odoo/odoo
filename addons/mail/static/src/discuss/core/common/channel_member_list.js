import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { ChannelActionDialog } from "@mail/discuss/core/common/channel_action_dialog";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";

import { Component, onWillRender, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import { useService } from "@web/core/utils/hooks";
import { useSearch } from "@mail/utils/common/hooks";

let nextId = 0;
const SEARCH_RESULT_LIMIT = 100;

/**
 * @typedef {Object} MemberCategory
 * @property {number} sequence sort key; lower is rendered first.
 * @property {(channel: import("models").DiscussChannel) => import("models").ChannelMember[]} getMembers
 * @property {string} label
 * @property {boolean} [showCount=true] whether to append the member count to the label.
 */

/** @type {MemberCategory[]} */
export const MEMBER_CATEGORIES = [
    { sequence: 10, getMembers: (ch) => ch.onlineMembers, label: _t("Online") },
    { sequence: 20, getMembers: (ch) => ch.offlineMembers, label: _t("Offline") },
    { sequence: 30, getMembers: (ch) => ch.unknownStatusMembers, label: _t("Others") },
];

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
        this.search = useSearch({
            fetch: async (term) => {
                await this.props.channel.searchChannelMembers(term);
                return this.hasFilteredMembers(this.computeCategories(term));
            },
        });
        this.categories = [];
        onWillRender(() => {
            this.categories = this.computeCategories(this.search.searchTerm);
        });
        onWillStart(() => {
            if (this.props.channel.fetchMembersState === "not_fetched") {
                this.props.channel.fetchChannelMembers();
            }
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.channel.fetchMembersState === "not_fetched") {
                nextProps.channel.fetchChannelMembers();
            }
            if (nextProps.channel.notEq(this.props.channel)) {
                this.search.reset();
            }
        });
    }

    /** @param {ReturnType<typeof ChannelMemberList.prototype.computeCategories>} categories */
    hasFilteredMembers(categories) {
        return categories.some((c) => c.filtered.length > 0);
    }

    get isSearchResultCapped() {
        if (!this.search.searchTerm) {
            return false;
        }
        return (
            this.categories.reduce((sum, c) => sum + c.matching.length, 0) >= SEARCH_RESULT_LIMIT
        );
    }

    get searchResultCapHint() {
        return _t("Showing first %(limit)s members. Narrow your search to see more.", {
            limit: SEARCH_RESULT_LIMIT,
        });
    }

    /** @param {string} searchTerm */
    computeCategories(searchTerm) {
        const term = searchTerm.toLowerCase();
        let remaining = SEARCH_RESULT_LIMIT;
        return [...MEMBER_CATEGORIES]
            .sort((a, b) => a.sequence - b.sequence)
            .map(({ getMembers, label, showCount = true }) => {
                const all = getMembers(this.props.channel);
                const matching = term
                    ? all.filter((m) => m.name?.toLowerCase().includes(term))
                    : all;
                const filtered = term ? matching.slice(0, Math.max(0, remaining)) : matching;
                remaining -= filtered.length;
                return { label, matching, filtered, showCount };
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
