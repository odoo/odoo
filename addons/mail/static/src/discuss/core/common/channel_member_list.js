import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { openChannelInvitationDialog } from "@mail/discuss/core/common/channel_invitation";
import { SearchInput } from "@mail/core/common/search_input";

import { Component, computed, props, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import { useService } from "@web/core/utils/hooks";
import { useOnChange, useSearch } from "@mail/utils/common/hooks";

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

export class ChannelMemberList extends Component {
    static components = { ActionPanel, ChannelMember, SearchInput };
    static template = "discuss.ChannelMemberList";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            channel: t.instanceOf(this.store["discuss.channel"].Class),
            close: t.function([]).optional(),
        });
        this.dialogService = useService("dialog");
        this.openChannelInvitationDialog = openChannelInvitationDialog;
        this.search = useSearch({
            fetch: async (term) => {
                await this.props.channel.searchChannelMembers(term);
                return this.hasFilteredMembers(this.computeCategories(term));
            },
        });
        this.categories = computed(() => this.computeCategories(this.search.searchTerm));
        useOnChange(
            () => [this.props.channel],
            (channel) => {
                if (channel.fetchMembersState === "not_fetched") {
                    channel.fetchChannelMembers();
                }
            }
        );
        useOnChange(
            () => [this.props.channel],
            () => this.search.reset(),
            { initialRun: false }
        );
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
            this.categories().reduce((sum, c) => sum + c.matching.length, 0) >= SEARCH_RESULT_LIMIT
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
}
