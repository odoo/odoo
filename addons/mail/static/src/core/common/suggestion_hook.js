import { isContentEditable, isTextNode } from "@html_editor/utils/dom_info";
import { rightPos } from "@html_editor/utils/position";
import {
    generatePartnerMentionElement,
    generateRoleMentionElement,
    generateSpecialMentionElement,
    generateThreadMentionElement,
} from "@mail/utils/common/format";
import { status, useComponent, useEffect, useState } from "@odoo/owl";
import { ConnectionAbortedError } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { createTextNode } from "@web/core/utils/xml";

export const DELAY_FETCH = 250;

export class UseSuggestion {
    constructor(comp) {
        this.comp = comp;
        this.fetchSuggestions = useDebounced(this.fetchSuggestions.bind(this), DELAY_FETCH);
        useEffect(
            () => {
                this.update();
                if (this.search.position === undefined || !this.search.delimiter) {
                    return; // nothing else to fetch
                }
                if (!this.composer.store.self_partner) {
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
            () => [
                this.composer.selection.start,
                this.composer.selection.end,
                this.composer.composerText,
                this.composer.composerHtml,
            ]
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
        this.composer.mentionedRoles.length = 0;
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
        let start = 0;
        let end = 0;
        let text = "";
        if (this.comp.composerService.htmlEnabled) {
            const selection = this.comp.editor.shared.selection.getEditableSelection();
            if (
                !isTextNode(selection.startContainer) ||
                !isContentEditable(selection.startContainer) ||
                !selection.isCollapsed
            ) {
                this.clearSearch();
                return;
            }
            start = selection.startOffset;
            end = selection.endOffset;
            text = selection.anchorNode.textContent;
        } else {
            start = this.composer.selection.start;
            end = this.composer.selection.end;
            text = this.composer.composerText;
        }
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
        const supportedDelimiters = this.suggestionService.getSupportedDelimiters(
            this.thread,
            this.comp.env
        );
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
            Object.assign(this.search, {
                delimiter: candidateDelimiter,
                position: candidatePosition,
                term: text.substring(candidatePosition + candidateDelimiter.length, start),
            });
            this.state.count++;
            return;
        }
        this.clearSearch();
    }
    get thread() {
        return this.composer.thread || this.composer.message?.thread;
    }
    insert(option) {
        let position = this.search.position + 1;
        if (
            [":", "::"].includes(this.search.delimiter) ||
            (this.comp.composerService.htmlEnabled && this.search.delimiter !== "/")
        ) {
            position = this.search.position;
        }
        if (this.comp.composerService.htmlEnabled) {
            const { startContainer, endContainer, endOffset } =
                this.comp.editor.shared.selection.getEditableSelection();
            this.comp.editor.shared.selection.setSelection({
                anchorNode: startContainer,
                anchorOffset: position,
                focusNode: endContainer,
                focusOffset: endOffset,
            });
        }
        if (option.partner) {
            this.composer.mentionedPartners.add({ id: option.partner.id });
        } else if (option.role) {
            this.composer.mentionedRoles.add(option.role);
        } else if (option.thread) {
            this.composer.mentionedChannels.add({ model: "discuss.channel", id: option.thread.id });
        } else if (option.cannedResponse) {
            this.composer.cannedResponses.push(option.cannedResponse);
        }
        if (this.comp.composerService.htmlEnabled) {
            let inlineElement;
            if (option.partner) {
                inlineElement = generatePartnerMentionElement(option.partner, this.thread);
            } else if (option.isSpecial) {
                inlineElement = generateSpecialMentionElement(option.label);
            } else if (option.role) {
                inlineElement = generateRoleMentionElement(option.role);
            } else if (option.thread) {
                inlineElement = generateThreadMentionElement(option.thread);
            } else {
                inlineElement = createTextNode(option.label);
            }
            this.comp.editor.shared.dom.insert(inlineElement);
            const [anchorNode, anchorOffset] = rightPos(inlineElement);
            this.comp.editor.shared.selection.setSelection({ anchorNode, anchorOffset });
            this.comp.editor.shared.dom.insert("\u00A0");
            this.comp.editor.shared.history.addStep();
        } else {
            // remove the user-typed search delimiter
            this.composer.composerText =
                this.composer.composerText.substring(0, position) +
                this.composer.composerText.substring(this.composer.selection.end);
            this.clearSearch();
            this.composer.insertText(`${option.label} `, position);
        }
    }
    update() {
        if (!this.search.delimiter) {
            return;
        }
        const { type, suggestions } = this.suggestionService.searchSuggestions(this.search, {
            thread: this.thread,
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
        if (!this.thread || status(this.comp) === "destroyed") {
            return;
        }
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
        if (!this.thread || status(this.comp) === "destroyed") {
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
