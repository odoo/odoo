import { onWillUnmount, proxy, status } from "@odoo/owl";

import { ConnectionAbortedError } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { useComponent, useLayoutEffect } from "@web/owl2/utils";

import {
    generateChannelMentionElement,
    generatePartnerMentionElement,
    generateRoleMentionElement,
    generateSpecialMentionElement,
} from "@mail/utils/common/format";
import { SearchState } from "@mail/utils/common/hooks";

/**
 * @typedef {Object} Option
 * @property {string} [buttonClass]
 * @property {string} [classList]
 * @property {number} [group]
 * @property {boolean} [isSpecial]
 * @property {string} [label]
 * @property {string} [optionTemplate]
 * @property {string} [title]
 * @property {boolean} [unselectable]
 * @property {import("models").ResRole} [role]
 * @property {import("models").ResPartner} [partner]
 * @property {import("models").Thread} [thread]
 * @property {import("models").CannedResponse} [cannedResponse]
 * @property {import("@web/core/emoji_picker/emoji_picker").Emoji} [emoji]
 * @property {string} [help]
 * @property {string} [source]
 */

/**
 * @typedef {import("models").ResPartner
 *   | import("models").ResRole
 *   | import("models").Thread
 *   | import("models").CannedResponse
 *   | import("@web/core/emoji_picker/emoji_picker").Emoji
 *   | import("@mail/core/common/store_service").SpecialMention} Suggestion
 */

/**
 * Encapsulates suggestion detection and search state shared by both
 * {@link UseSuggestion} (plain-text composer hook) and {@link MentionPlugin}
 * (html composer plugin).
 *
 * Uses only `proxy` and `SearchState` — no Owl lifecycle hooks — so it works in
 * any context. Call `dispose()` to clean up (from `onWillUnmount` in a
 * component, or via the plugin's cleanups).
 */
export class SuggestionCore {
    /** @type {AbortController|undefined} */
    abortController;
    /** @type {() => boolean} */
    canFetch;
    /** @type {{ delimiter: string|undefined, position: number|undefined, term: string }} */
    detection;
    /** @type {(() => string|undefined)|undefined} */
    getComposerType;
    /** @type {(() => import("models").Thread|undefined)|undefined} */
    getThread;
    /** @type {import("@mail/utils/common/hooks").SearchState} */
    search;
    /** @type {Object} The `mail.suggestion` service. */
    suggestionService;

    /**
     * @param {Object} options
     * @param {() => boolean} [options.canFetch] Guards the server fetch (e.g.
     *   destroyed / guest checks). Defaults to always-true.
     * @param {() => string|undefined} [options.getComposerType]
     * @param {() => import("models").Thread|undefined} [options.getThread]
     * @param {Object} options.suggestionService
     */
    constructor({ canFetch, getComposerType, getThread, suggestionService } = {}) {
        this.canFetch = canFetch ?? (() => true);
        this.getComposerType = getComposerType;
        this.getThread = getThread;
        this.suggestionService = suggestionService;
        this.detection = proxy({ delimiter: undefined, position: undefined, term: "" });
        this.search = new SearchState({
            fetch: this.fetchSuggestions.bind(this),
            filter: this.update.bind(this),
            deps: () => [this.detection.delimiter, this.detection.position],
            isActive: () => !!this.detection.delimiter,
        });
    }

    /** @returns {string|undefined} */
    get composerType() {
        return this.getComposerType?.();
    }

    /** @returns {import("models").Thread|undefined} */
    get thread() {
        return this.getThread?.();
    }

    clearSearch() {
        Object.assign(this.detection, { delimiter: undefined, position: undefined, term: "" });
        this.search.reset();
    }

    /** Stops the internal `SearchState` effect and resets state. */
    dispose() {
        this.search.dispose();
    }

    /**
     * Scans backward from `start` in `text` for a suggestion delimiter, then
     * updates `detection` + `search.searchTerm` on success, or clears the
     * search when no delimiter is found.
     *
     * @param {number} start Cursor offset within `text`.
     * @param {string} text Full text content of the current editor node.
     */
    processDetection(start, text) {
        const candidatePositions = [];
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
        if (this.detection.position !== undefined && this.detection.position < start) {
            candidatePositions.push(this.detection.position);
        }
        const supportedDelimiters = this.suggestionService.getSupportedDelimiters(this.thread);
        for (const candidatePosition of candidatePositions) {
            if (candidatePosition < 0 || candidatePosition >= text.length) {
                continue;
            }
            const delimiter = this.findDelimiter(text, candidatePosition, start, supportedDelimiters);
            if (!delimiter) {
                continue;
            }
            const charBefore = text[candidatePosition - 1];
            if (charBefore && !/\s/.test(charBefore)) {
                continue;
            }
            Object.assign(this.detection, {
                delimiter,
                position: candidatePosition,
                term: text.substring(candidatePosition + delimiter.length, start),
            });
            this.search.searchTerm = this.detection.term;
            return;
        }
        this.clearSearch();
    }

    /**
     * Returns the most specific matching delimiter at `candidatePosition`, or
     * `undefined` if none qualify.
     *
     * @param {string} text
     * @param {number} candidatePosition
     * @param {number} start
     * @param {Array<[string, number|undefined, number|undefined]>} supportedDelimiters
     * @returns {string|undefined}
     */
    findDelimiter(text, candidatePosition, start, supportedDelimiters) {
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
    }

    /**
     * `SearchState` filter: synchronous local lookup capped at 8 results.
     *
     * @returns {{ type: string, suggestions: Suggestion[] }|undefined}
     */
    update() {
        if (!this.detection.delimiter) {
            return undefined;
        }
        const { type, suggestions } = this.suggestionService.searchSuggestions(this.detection, {
            composerType: this.composerType,
            thread: this.thread,
        });
        if (!suggestions.length) {
            return undefined;
        }
        // arbitrary limit to avoid displaying too many elements at once
        // ideally a load more mechanism should be introduced
        const limit = 8;
        suggestions.length = Math.min(suggestions.length, limit);
        return { type, suggestions };
    }

    /**
     * `SearchState` fetch: aborts any in-flight request, then resolves to
     * `false` when the server returns nothing (lets `SearchState` skip
     * narrower fetches via `lastEmptyTerm`).
     *
     * @returns {Promise<false|undefined>}
     */
    async fetchSuggestions() {
        if (!this.canFetch()) {
            return;
        }
        try {
            this.abortController?.abort();
            this.abortController = new AbortController();
            await this.suggestionService.fetchSuggestions(this.detection, {
                abortSignal: this.abortController.signal,
                composerType: this.composerType,
                thread: this.thread,
            });
        } catch (e) {
            if (e instanceof ConnectionAbortedError) {
                return;
            }
            throw e;
        }
        if (!this.canFetch()) {
            return;
        }
        const { suggestions } = this.suggestionService.searchSuggestions(this.detection, {
            thread: this.thread,
        });
        return suggestions.length === 0 ? false : undefined;
    }
}

export class UseSuggestion {
    /** @type {import("@mail/core/common/composer").Composer} */
    comp;

    constructor(comp) {
        this.comp = comp;
        this.suggestion = new SuggestionCore({
            canFetch: () =>
                !!this.thread &&
                status(this.comp) !== "destroyed" &&
                !!this.composer.store.self_user,
            getComposerType: () => this.comp.props.type,
            getThread: () => this.thread,
            suggestionService: useService("mail.suggestion"),
        });
        useLayoutEffect(
            () => this.detect(),
            () => [this.composer.selection.start, this.composer.selection.end, this.composer.composerText]
        );
        onWillUnmount(() => this.suggestion.dispose());
    }
    get composer() {
        return this.comp.props.composer;
    }
    /** @returns {import("@mail/utils/common/hooks").SearchState} */
    get search() {
        return this.suggestion.search;
    }
    get thread() {
        return this.composer.thread || this.composer.message?.thread;
    }
    clearRawMentions() {
        this.composer.mentionedChannels.length = 0;
        this.composer.mentionedPartners.length = 0;
        this.composer.mentionedRoles.length = 0;
    }
    clearCannedResponses() {
        this.composer.cannedResponses = [];
    }
    detect() {
        const start = this.composer.selection.start;
        if (start !== this.composer.selection.end) {
            // avoid interfering with multi-char selection
            this.suggestion.clearSearch();
            return;
        }
        this.suggestion.processDetection(start, this.composer.composerText);
    }
    insert(option) {
        if (option.partner) {
            this.composer.mentionedPartners.add({ id: option.partner.id });
        } else if (option.role) {
            this.composer.mentionedRoles.add(option.role);
        } else if (option.channel) {
            this.composer.mentionedChannels.add(option.channel.id);
        } else if (option.cannedResponse) {
            this.composer.cannedResponses.push(option.cannedResponse);
        }
        // plain-text: ":"/"::" anchor on the delimiter, others step past it
        const { delimiter, position } = this.suggestion.detection;
        const insertAt = [":", "::"].includes(delimiter) ? position : position + 1;
        // remove the user-typed search delimiter
        this.composer.composerText =
            this.composer.composerText.substring(0, insertAt) +
            this.composer.composerText.substring(this.composer.selection.end);
        this.suggestion.clearSearch();
        this.composer.insertText(`${option.label} `, insertAt);
    }
}

export function useSuggestion() {
    return new UseSuggestion(useComponent());
}

/**
 * Maps raw suggestion records to navigable list option objects for all suggestion types.
 *
 * @param {string} type
 * @param {Suggestion[]} suggestions
 * @param {Object} [params]
 * @param {import("models").Thread} [params.thread] The thread where the suggestion is being
 *   composed. Used e.g. to resolve partner display names in context and stored on the resulting
 *   Option so that consumers (insertion handlers, mention templates) can access it.
 * @returns {{ optionTemplate?: string, options: Option[] }}
 */
export function mapSuggestionsToOptions(type, suggestions, { thread } = {}) {
    const classList = "o-mail-Composer-suggestion";
    switch (type) {
        case "Partner":
            return {
                optionTemplate: "mail.Composer.suggestionPartner",
                options: suggestions.map((suggestion) => {
                    if (suggestion.isSpecial) {
                        return {
                            ...suggestion,
                            group: 3,
                            optionTemplate: "mail.Composer.suggestionSpecial",
                            classList,
                        };
                    }
                    if (suggestion?.Model?.getName?.() === "res.role") {
                        return {
                            group: 2,
                            label: suggestion.name,
                            role: suggestion,
                            thread,
                            optionTemplate: "mail.Composer.suggestionRole",
                            classList,
                        };
                    }
                    return {
                        group: 1,
                        label: thread?.getPersonaName(suggestion) ?? suggestion.name,
                        partner: suggestion,
                        thread,
                        classList,
                    };
                }),
            };
        case "discuss.channel":
            return {
                optionTemplate: "mail.Composer.suggestionChannel",
                options: suggestions.map((suggestion) => ({
                    label: suggestion.fullNameWithParent,
                    channel: suggestion,
                    classList,
                })),
            };
        case "ChannelCommand":
            return {
                optionTemplate: "mail.Composer.suggestionChannelCommand",
                options: suggestions.map((suggestion) => ({
                    label: suggestion.name,
                    help: suggestion.help,
                    classList,
                })),
            };
        case "mail.canned.response":
            return {
                optionTemplate: "mail.Composer.suggestionCannedResponse",
                options: suggestions.map((suggestion) => ({
                    cannedResponse: suggestion,
                    label: suggestion.substitution,
                    source: suggestion.source,
                    title: suggestion.substitution,
                    classList,
                })),
            };
        case "emoji":
            return {
                optionTemplate: "mail.Composer.suggestionEmoji",
                options: suggestions.map((suggestion) => ({
                    emoji: suggestion,
                    label: suggestion.codepoints,
                })),
            };
        default:
            return { options: [] };
    }
}

/**
 * @param {Option} option
 * @param {Object} [params]
 * @param {import("models").Thread} [params.thread] The thread being viewed by the
 *   user, needed to generate mention links that point back to the right record.
 */
export function makeMentionFromOption(option, { thread } = {}) {
    let inlineElement;
    if (option.partner) {
        inlineElement = generatePartnerMentionElement(option.partner, { thread });
    } else if (option.isSpecial) {
        inlineElement = generateSpecialMentionElement(option.label);
    } else if (option.role) {
        inlineElement = generateRoleMentionElement(option.role);
    } else if (option.channel) {
        inlineElement = generateChannelMentionElement(option.channel);
    } else {
        inlineElement = document.createTextNode(option.label);
    }
    return inlineElement;
}
