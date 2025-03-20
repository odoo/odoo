import { useComponent, useEffect, useState, toRaw } from "@odoo/owl";
import { ConnectionAbortedError } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { loadEmoji } from "@web/core/emoji_picker/emoji_picker";
import { fuzzyLookup } from "@web/core/utils/search";

import { partnerCompareRegistry } from "@mail/core/common/partner_compare";
import { cleanTerm } from "@mail/utils/common/format";
import { ormOnInput } from "@mail/utils/common/hooks";

/**
 * @property {import("@mail/core/common/composer").Composer} param.composer
 */
export class UseSuggestion {

    /**
     * Returns list of supported delimiters, each supported
     * delimiter is in an array [a, b, c] where:
     * - a: chars to trigger
     * - b: (optional) if set, the exact position in composer text input to allow using this delimiter
     * - c: (optional) if set, this is the minimum amount of extra char after delimiter to allow using this delimiter
     *
     * @param {import('models').Thread} [thread]
     * @returns {Array<[string, number, number]>}
     */
    static getSupportedDelimiters(thread) {
        return [["@"], ["#"], ["::"], [":", undefined, 2]];
    }

    constructor({
        thread,
        composer,
        env,
        store,
    }) {
        this.thread = thread;
        this.composer = composer;
        this.store = store;
        this.emojis;
        this.env = env;
        this.ormOnInput = ormOnInput(this.env.services["orm"]);
    }
    search = {
        delimiter: undefined,
        position: undefined,
    };
    lastFetchedSearch;
    get isSearchMoreSpecificThanLastFetch() {
        return (
            this.lastFetchedSearch.delimiter === this.search.delimiter &&
            this.state.term.startsWith(this.lastFetchedSearch.term) &&
            this.lastFetchedSearch.position >= this.search.position
        );
    }
    clearRawMentions() {
        this.composer.mentionedChannels.length = 0;
        this.composer.mentionedPartners.length = 0;
    }
    clearCannedResponses() {
        this.composer.cannedResponses = [];
    }
    clearSearch() {
        this.search.delimiter = undefined;
        this.search.position = undefined;
        this.state.term = "";
        this.state.items = undefined;
    }
    detect() {
        const { start, end } = this.composer.selection;
        const text = this.composer.text;
        if (start !== end) {
            // avoid interfering with multi-char selection
            this.clearSearch();
            return;
        }
        const candidatePositions = [];
        // consider the chars before the current cursor position
        let numberOfSpaces = 0;
        for (let index = start - 1; index >= 0; --index) {
            if (/\s/.test(text[index])) {
                numberOfSpaces++;
                if (numberOfSpaces === 2) {
                    // The consideration stops after the second space since
                    // a majority of partners have a two-word name. This
                    // removes the need to check for mentions following a
                    // delimiter used earlier in the content.
                    break;
                }
            }
            candidatePositions.push(index);
        }
        // keep the current delimiter if it is still valid
        if (this.search.position !== undefined && this.search.position < start) {
            candidatePositions.push(this.search.position);
        }
        const supportedDelimiters = UseSuggestion.getSupportedDelimiters(this.thread);
        for (const candidatePosition of candidatePositions) {
            if (candidatePosition < 0 || candidatePosition >= text.length) {
                continue;
            }

            const findAppropriateDelimiter = () => {
                let goodCandidate;
                for (const [delimiter, allowedPosition, minCharCountAfter] of supportedDelimiters) {
                    if (
                        text.substring(candidatePosition).startsWith(delimiter) && // delimiter is used
                        (allowedPosition === undefined || allowedPosition === candidatePosition) && // delimiter is allowed position
                        (minCharCountAfter === undefined ||
                            start - candidatePosition - delimiter.length + 1 > minCharCountAfter) && // delimiter is allowed (enough custom char typed after)
                        (!goodCandidate || delimiter.length > goodCandidate) // delimiter is more specific
                    ) {
                        goodCandidate = delimiter;
                    }
                }
                return goodCandidate;
            };

            const candidateDelimiter = findAppropriateDelimiter();
            if (!candidateDelimiter) {
                continue;
            }
            const charBeforeCandidate = text[candidatePosition - 1];
            if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                continue;
            }

            this.search.delimiter = candidateDelimiter;
            this.search.position = candidatePosition;
            this.state.term = text.substring(candidatePosition + candidateDelimiter.length, start);
            this.state.count++;
            return;
        }
        this.clearSearch();
    }
    insert(option) {
        const position = this.composer.selection.start;
        const text = this.composer.text;
        let before = text.substring(0, this.search.position + 1);
        let after = text.substring(position, text.length);
        if ([":", "::"].includes(this.search.delimiter)) {
            before = text.substring(0, this.search.position);
            after = text.substring(position, text.length);
        }
        if (option.partner) {
            this.composer.mentionedPartners.add({
                id: option.partner.id,
                type: "partner",
            });
        }
        if (option.thread) {
            this.composer.mentionedChannels.add({
                model: "discuss.channel",
                id: option.thread.id,
            });
        }
        if (option.cannedResponse) {
            this.composer.cannedResponses.push(option.cannedResponse);
        }
        this.clearSearch();
        this.composer.text = before + option.label + " " + after;
        this.composer.selection.start = before.length + option.label.length + 1;
        this.composer.selection.end = before.length + option.label.length + 1;
        this.composer.forceCursorMove = true;
    }
    update() {
        if (!this.search.delimiter) {
            return;
        }
        const { type, suggestions } = this.searchSuggestions({ sort: true });
        if (!suggestions.length) {
            this.state.items = undefined;
            return;
        }
        // arbitrary limit to avoid displaying too many elements at once
        // ideally a load more mechanism should be introduced
        const limit = 8;
        suggestions.length = Math.min(suggestions.length, limit);
        this.state.items = { type, suggestions };
    }

    async fetchSuggestions() {
        let resetFetchingState = true;
        try {
            const cleanedSearchTerm = cleanTerm(this.state.term);
            switch (this.search.delimiter) {
                case "@": {
                    await this.fetchPartners(cleanedSearchTerm, this.thread);
                    break;
                }
                case "#":
                    await this.fetchThreads(cleanedSearchTerm);
                    break;
                case "::":
                    await this.store.cannedReponses.fetch();
                    break;
                case ":": {
                    const { emojis } = await loadEmoji();
                    this.emojis = emojis;
                    break;
                }
            }
        } catch (e) {
            this.lastFetchedSearch = null;
            if (e instanceof ConnectionAbortedError) {
                resetFetchingState = false;
                return;
            }
            throw e;
        } finally {
            if (resetFetchingState) {
                this.state.isFetching = false;
            }
        }
        this.update();
        this.lastFetchedSearch = {
            ...this.search,
            term: this.state.term,
            count: this.state.items?.suggestions.length ?? 0,
        };
        if (!this.state.items?.suggestions.length) {
            this.clearSearch();
        }
    }

    /**
     * @param {string} term
     * @param {import("models").Thread} [thread]
     */
    async fetchPartners(term, thread) {
        const kwargs = { search: term };
        if (thread?.model === "discuss.channel") {
            kwargs.channel_id = thread.id;
        }
        const data = await this.ormOnInput(
            "res.partner",
            thread?.model === "discuss.channel"
                ? "get_mention_suggestions_from_channel"
                : "get_mention_suggestions",
            [],
            kwargs,
        );
        this.store.insert(data);
    }

    /**
     * @param {string} term
     */
    async fetchThreads(term) {
        const suggestedThreads = await this.ormOnInput(
            "discuss.channel",
            "get_mention_suggestions",
            [],
            { search: term },
        );
        this.store.Thread.insert(suggestedThreads);
    }

    searchCannedResponseSuggestions(cleanedSearchTerm, sort) {
        const cannedResponses = Object.values(this.store["mail.canned.response"].records).filter(
            (cannedResponse) => cleanTerm(cannedResponse.source).includes(cleanedSearchTerm)
        );
        const sortFunc = (c1, c2) => {
            const cleanedName1 = cleanTerm(c1.source);
            const cleanedName2 = cleanTerm(c2.source);
            if (
                cleanedName1.startsWith(cleanedSearchTerm) &&
                !cleanedName2.startsWith(cleanedSearchTerm)
            ) {
                return -1;
            }
            if (
                !cleanedName1.startsWith(cleanedSearchTerm) &&
                cleanedName2.startsWith(cleanedSearchTerm)
            ) {
                return 1;
            }
            if (cleanedName1 < cleanedName2) {
                return -1;
            }
            if (cleanedName1 > cleanedName2) {
                return 1;
            }
            return c1.id - c2.id;
        };
        return {
            type: "mail.canned.response",
            suggestions: sort ? cannedResponses.sort(sortFunc) : cannedResponses,
        };
    }

    searchEmojisSuggestions(cleanedSearchTerm) {
        let emojis = [];
        if (this.emojis && cleanedSearchTerm) {
            emojis = fuzzyLookup(cleanedSearchTerm, this.emojis, (emoji) => emoji.shortcodes);
        }
        return {
            type: "emoji",
            suggestions: emojis,
        };
    }

    /**
     * Returns suggestions that match the given search term from specified type.
     */
    searchSuggestions({ sort } = { sort: false }) {
        const cleanedSearchTerm = cleanTerm(this.state.term);
        switch (this.search.delimiter) {
            case "@": {
                return this.searchPartnerSuggestions(cleanedSearchTerm, sort);
            }
            case "#":
                return this.searchChannelSuggestions(cleanedSearchTerm, sort);
            case "::":
                return this.searchCannedResponseSuggestions(cleanedSearchTerm, sort);
            case ":":
                return this.searchEmojisSuggestions(cleanedSearchTerm);
        }
        return {
            type: undefined,
            suggestions: [],
        };
    }

    getPartnerSuggestions(thread) {
        let partners;
        const isNonPublicChannel =
            thread &&
            (thread.channel_type === "group" ||
                thread.channel_type === "chat" ||
                (thread.channel_type === "channel" &&
                    (thread.parent_channel_id || thread).group_public_id));
        if (isNonPublicChannel) {
            // Only return the channel members when in the context of a
            // group restricted channel. Indeed, the message with the mention
            // would be notified to the mentioned partner, so this prevents
            // from inadvertently leaking the private message to the
            // mentioned partner.
            partners = thread.channel_member_ids
                .map((member) => member.persona)
                .filter((persona) => persona.type === "partner");
            if (thread.channel_type === "channel") {
                const group = (thread.parent_channel_id || thread).group_public_id;
                partners = new Set([...partners, ...(group?.personas ?? [])]);
            }
        } else {
            partners = Object.values(this.store.Persona.records).filter((persona) => {
                if (thread?.model !== "discuss.channel" && persona.eq(this.store.odoobot)) {
                    return false;
                }
                return persona.type === "partner";
            });
        }
        return partners;
    }

    searchPartnerSuggestions(cleanedSearchTerm, sort) {
        const partners = this.getPartnerSuggestions(toRaw(this.thread));
        const suggestions = [];
        for (const partner of partners) {
            if (!partner.name) {
                continue;
            }
            if (
                cleanTerm(partner.name).includes(cleanedSearchTerm) ||
                (partner.email && cleanTerm(partner.email).includes(cleanedSearchTerm))
            ) {
                suggestions.push(partner);
            }
        }
        suggestions.push(
            ...this.store.specialMentions.filter(
                (special) =>
                    this.thread &&
                    special.channel_types.includes(this.thread.channel_type) &&
                    cleanedSearchTerm.length >= Math.min(4, special.label.length) &&
                    (special.label.startsWith(cleanedSearchTerm) ||
                        cleanTerm(special.description.toString()).includes(cleanedSearchTerm))
            )
        );
        return {
            type: "Partner",
            suggestions: sort
                ? [...this.sortPartnerSuggestions(suggestions, cleanedSearchTerm)]
                : suggestions,
        };
    }

    /**
     * @param {[import("models").Persona | import("@mail/core/common/store_service").SpecialMention]} [partners]
     * @param {String} [searchTerm]
     * @param {import("models").Thread} thread
     * @returns {[import("models").Persona]}
     */
    sortPartnerSuggestions(partners, searchTerm = "") {
        const cleanedSearchTerm = cleanTerm(searchTerm);
        const compareFunctions = partnerCompareRegistry.getAll();
        const context = this.sortPartnerSuggestionsContext();
        return partners.sort((p1, p2) => {
            p1 = toRaw(p1);
            p2 = toRaw(p2);
            if (p1.isSpecial || p2.isSpecial) {
                return 0;
            }
            for (const fn of compareFunctions) {
                const result = fn(p1, p2, {
                    env: this.env,
                    searchTerm: cleanedSearchTerm,
                    thread: this.thread,
                    context,
                });
                if (result !== undefined) {
                    return result;
                }
            }
        });
    }

    sortPartnerSuggestionsContext() {
        return {};
    }

    searchChannelSuggestions(cleanedSearchTerm, sort) {
        const suggestionList = Object.values(this.store.Thread.records).filter(
            (thread) =>
                thread.channel_type === "channel" &&
                thread.displayName &&
                cleanTerm(thread.displayName).includes(cleanedSearchTerm)
        );
        const sortFunc = (c1, c2) => {
            const isPublicChannel1 = c1.channel_type === "channel" && !c2.authorizedGroupFullName;
            const isPublicChannel2 = c2.channel_type === "channel" && !c2.authorizedGroupFullName;
            if (isPublicChannel1 && !isPublicChannel2) {
                return -1;
            }
            if (!isPublicChannel1 && isPublicChannel2) {
                return 1;
            }
            if (c1.hasSelfAsMember && !c2.hasSelfAsMember) {
                return -1;
            }
            if (!c1.hasSelfAsMember && c2.hasSelfAsMember) {
                return 1;
            }
            const cleanedDisplayName1 = cleanTerm(c1.displayName);
            const cleanedDisplayName2 = cleanTerm(c2.displayName);
            if (
                cleanedDisplayName1.startsWith(cleanedSearchTerm) &&
                !cleanedDisplayName2.startsWith(cleanedSearchTerm)
            ) {
                return -1;
            }
            if (
                !cleanedDisplayName1.startsWith(cleanedSearchTerm) &&
                cleanedDisplayName2.startsWith(cleanedSearchTerm)
            ) {
                return 1;
            }
            if (cleanedDisplayName1 < cleanedDisplayName2) {
                return -1;
            }
            if (cleanedDisplayName1 > cleanedDisplayName2) {
                return 1;
            }
            return c1.id - c2.id;
        };
        return {
            type: "Thread",
            suggestions: sort ? suggestionList.sort(sortFunc) : suggestionList,
        };
    }
}

export function useSuggestion() {
    const comp = useComponent();
    const store = useService("mail.store");
    const suggestion = new UseSuggestion({
        env: comp.env,
        composer: comp.props.composer,
        thread: comp.props.composer?.thread || comp.props.composer?.message.thread,
        store
    });
    suggestion.state = useState({
        term: "",
        count: 0,
        items: undefined,
        isFetching: false,
    });
    useEffect(
        () => {
            suggestion.update();
            if (suggestion.search.position === undefined || !suggestion.search.delimiter) {
                return; // nothing else to fetch
            }
            if (suggestion.composer.store.self.type !== "partner") {
                return; // guests cannot access fetch suggestion method
            }
            if (
                suggestion.lastFetchedSearch?.count === 0 &&
                (!suggestion.search.delimiter || suggestion.isSearchMoreSpecificThanLastFetch)
            ) {
                return; // no need to fetch since this is more specific than last and last had no result
            }
            suggestion.fetchSuggestions();
        },
        () => [suggestion.search.delimiter, suggestion.search.position, suggestion.state.term]
    );
    useEffect(
        () => {
            if (suggestion.composer) {
                suggestion.detect();
            }
        },
        () => [suggestion.composer?.selection.start, suggestion.composer?.selection.end, suggestion.composer?.text]
    );
    return suggestion;
}
