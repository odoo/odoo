import { status, useComponent, useEffect, useState } from "@odoo/owl";
import { ConnectionAbortedError } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

class UseSuggestion {
    constructor(comp) {
        this.comp = comp;
        this.fetchSuggestions = useDebounced(this.fetchSuggestions.bind(this), 250);
        useEffect(
            () => {
                this.update();
                if (this.search.position === undefined || !this.search.delimiter) {
                    return; // nothing else to fetch
                }
                if (this.composer.store.self.type !== "partner") {
                    return; // guests cannot access fetch suggestion method
                }
                if (
                    this.lastFetchedSearch?.count === 0 &&
                    (!this.search.delimiter || this.isSearchMoreSpecificThanLastFetch)
                ) {
                    return; // no need to fetch since this is more specific than last and last had no result
                }
                this.fetchSuggestions();
            },
            () => [this.search.delimiter, this.search.position, this.search.term]
        );
        useEffect(
            () => {
                this.detect();
            },
            () => [this.composer.selection.start, this.composer.selection.end, this.composer.text]
        );
    }
    /** @type {import("@mail/core/common/composer").Composer} */
    comp;
    get composer() {
        return this.comp.props.composer;
    }
    suggestionService = useService("mail.suggestion");
    state = useState({
        count: 0,
        items: undefined,
        isFetching: false,
    });
    search = {
        delimiter: undefined,
        position: undefined,
        term: "",
    };
    lastFetchedSearch;
    get isSearchMoreSpecificThanLastFetch() {
        return (
            this.lastFetchedSearch.delimiter === this.search.delimiter &&
            this.search.term.startsWith(this.lastFetchedSearch.term) &&
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
        Object.assign(this.search, {
            delimiter: undefined,
            position: undefined,
            term: "",
        });
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
        const supportedDelimiters = this.suggestionService.getSupportedDelimiters(this.thread);
        for (const candidatePosition of candidatePositions) {
            if (candidatePosition < 0 || candidatePosition >= text.length) {
                continue;
            }
            const candidateChar = text[candidatePosition];
            if (
                !supportedDelimiters.find(
                    ([delimiter, allowedPosition]) =>
                        delimiter === candidateChar &&
                        (allowedPosition === undefined || allowedPosition === candidatePosition)
                )
            ) {
                continue;
            }
            const charBeforeCandidate = text[candidatePosition - 1];
            if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                continue;
            }
            Object.assign(this.search, {
                delimiter: candidateChar,
                position: candidatePosition,
                term: text.substring(candidatePosition + 1, start),
            });
            this.state.count++;
            return;
        }
        this.clearSearch();
    }
    get thread() {
        return this.composer.thread || this.composer.message.thread;
    }
    insert(option) {
        const position = this.composer.selection.start;
        const text = this.composer.text;
        let before = text.substring(0, this.search.position + 1);
        let after = text.substring(position, text.length);
        if (this.search.delimiter === ":") {
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
        const { type, suggestions } = this.suggestionService.searchSuggestions(this.search, {
            thread: this.thread,
            sort: true,
        });
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
            this.abortController?.abort();
            this.abortController = new AbortController();
            this.state.isFetching = true;
            await this.suggestionService.fetchSuggestions(this.search, {
                thread: this.thread,
                abortSignal: this.abortController.signal,
            });
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
        if (status(this.comp) === "destroyed") {
            return;
        }
        this.update();
        this.lastFetchedSearch = {
            ...this.search,
            count: this.state.items?.suggestions.length ?? 0,
        };
        if (!this.state.items?.suggestions.length) {
            this.clearSearch();
        }
    }
}

export function useSuggestion() {
    return new UseSuggestion(useComponent());
}
