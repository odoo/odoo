import { useSequential } from "@mail/utils/common/hooks";
import { status, useComponent, useEffect, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

class UseSuggestion {
    constructor(comp) {
        this.comp = comp;
        useEffect(
            (delimiter, position, term) => {
                this.update();
                if (this.search.position === undefined || !this.search.delimiter) {
                    return; // nothing else to fetch
                }
                this.sequential(async () => {
                    if (
                        this.search.delimiter !== delimiter ||
                        this.search.position !== position ||
                        this.search.term !== term
                    ) {
                        return; // ignore obsolete call
                    }
                    await this.suggestionService.fetchSuggestions(this.search, {
                        thread: this.thread,
                    });
                    if (status(comp) === "destroyed") {
                        return;
                    }
                    this.update();
                    if (
                        this.search.delimiter === delimiter &&
                        this.search.position === position &&
                        this.search.term === term &&
                        !this.state.items?.suggestions.length
                    ) {
                        this.clearSearch();
                    }
                });
            },
            () => {
                return [this.search.delimiter, this.search.position, this.search.term];
            }
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
    sequential = useSequential();
    suggestionService = useService("mail.suggestion");
    state = useState({
        count: 0,
        items: undefined,
    });
    search = {
        delimiter: undefined,
        position: undefined,
        term: "",
    };
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
}

export function useSuggestion() {
    return new UseSuggestion(useComponent());
}
