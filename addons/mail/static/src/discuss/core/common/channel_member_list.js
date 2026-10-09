import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { ChannelMember } from "@mail/discuss/core/common/channel_member";
import { openChannelInvitationDialog } from "@mail/discuss/core/common/channel_invitation";
import { SearchInput } from "@mail/core/common/search_input";
import { computedShallowEqual } from "@mail/utils/common/signal";

import { Component, t, useOnChange, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

import { useService } from "@web/core/utils/hooks";
import { useSearch } from "@mail/utils/common/hooks";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

const SEARCH_RESULT_LIMIT = 100;

/**
 * @typedef {Object} MemberCategory
 * @property {number} sequence sort key; lower is rendered first.
 * @property {(channel: import("models").DiscussChannel) => import("models").ChannelMember[]} getMembers
 * @property {TranslatedString} label
 * @property {boolean} [showCount=true] whether to append the member count to the label.
 * @property {number} [sequenceGroup] categories sharing this key are rendered inside a common container.
 * @property {string} [icon] class of an icon shown before the section label.
 * @property {string} [headerClass] extra class applied to the section header.
 * @property {string} [groupClass] extra class applied to the `sequenceGroup` container
 * while this category has members.
 */

/**
 * A {@link MemberCategory} resolved against a search term: the definition fields
 * are carried over (minus the source-only `getMembers`) and enriched
 * with the members it matched.
 *
 * @typedef {Omit<MemberCategory, "getMembers"> & ResolvedMembers} ComputedMemberCategory
 */

/**
 * @typedef {Object} ResolvedMembers
 * @property {import("models").ChannelMember[]} matching members whose name matches the search term.
 * @property {import("models").ChannelMember[]} filtered `matching` capped to the search-result limit; the members actually rendered.
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
        this.ancestors = useAncestors();
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]),
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
        this.categories = computedShallowEqual(
            () => this.computeCategories(this.search.searchTerm),
            { nested: true }
        );
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

    /** @param {ComputedMemberCategory[]} categories */
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

    /**
     * @param {string} searchTerm
     */
    computeCategories(searchTerm) {
        const term = searchTerm.toLowerCase();
        let remaining = SEARCH_RESULT_LIMIT;
        const shownMemberIds = new Set();
        return [...MEMBER_CATEGORIES]
            .sort((a, b) => a.sequence - b.sequence)
            .map(({ getMembers, showCount = true, ...definition }) => {
                const all = getMembers(this.props.channel).filter((m) => {
                    if (shownMemberIds.has(m.id)) {
                        return false;
                    }
                    shownMemberIds.add(m.id);
                    return true;
                });
                const matching = term
                    ? all.filter((m) => m.name?.toLowerCase().includes(term))
                    : all;
                const filtered = term ? matching.slice(0, Math.max(0, remaining)) : matching;
                remaining -= filtered.length;
                return { ...definition, matching, filtered, showCount };
            });
    }

    /**
     * Bundle consecutive categories sharing a `sequenceGroup` key so they can be
     * rendered inside a common container. Categories without one each stand alone.
     *
     * @param {ComputedMemberCategory[]} categories
     */
    groupedCategories(categories) {
        const groups = [];
        for (const category of categories) {
            const last = groups.at(-1);
            if (category.sequenceGroup && last?.sequenceGroup === category.sequenceGroup) {
                last.categories.push(category);
            } else {
                groups.push({ sequenceGroup: category.sequenceGroup, categories: [category] });
            }
        }
        return groups;
    }

    /**
     * @param {{ categories: ComputedMemberCategory[] }} group
     */
    groupClass(group) {
        return group.categories
            .filter((category) => category.filtered.length > 0 && category.groupClass)
            .map((category) => category.groupClass)
            .join(" ");
    }
}
