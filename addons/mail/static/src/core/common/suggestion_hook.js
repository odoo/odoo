/* @odoo-module */

import { useComponent, useEffect, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export function useSuggestion() {
    const comp = useComponent();
    /** @type {import("@mail/core/common/suggestion_service").SuggestionService} */
    const suggestionService = useService("mail.suggestion");
    const self = {
        clearRawMentions() {
            comp.props.composer.rawMentions.partnerIds.length = 0;
            comp.props.composer.rawMentions.threadIds.length = 0;
        },
        clearCannedReponses() {
            comp.props.composer.cannedResponseIds.clear();
        },
        clearSearch() {
            Object.assign(self.search, {
                delimiter: undefined,
                position: undefined,
                term: undefined,
            });
            self.state.items = undefined;
        },
        detect() {
            const selectionEnd = comp.props.composer.selection.end;
            const selectionStart = comp.props.composer.selection.start;
            const content = comp.props.composer.textInputContent;
            if (selectionStart !== selectionEnd) {
                // avoid interfering with multi-char selection
                self.clearSearch();
            }
            const candidatePositions = [];
            // keep the current delimiter if it is still valid
            if (self.search.position !== undefined && self.search.position < selectionStart) {
                candidatePositions.push(self.search.position);
            }
            // consider the char before the current cursor position if the
            // current delimiter is no longer valid (or if there is none)
            if (selectionStart > 0) {
                candidatePositions.push(selectionStart - 1);
            }
            const supportedDelimiters = suggestionService.getSupportedDelimiters(
                comp.props.composer.thread
            );
            for (const candidatePosition of candidatePositions) {
                if (candidatePosition < 0 || candidatePosition >= content.length) {
                    continue;
                }
                const candidateChar = content[candidatePosition];
                if (
                    !supportedDelimiters.find(
                        ([delimiter, allowedPosition]) =>
                            delimiter === candidateChar &&
                            (allowedPosition === undefined || allowedPosition === candidatePosition)
                    )
                ) {
                    continue;
                }
                const charBeforeCandidate = content[candidatePosition - 1];
                if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                    continue;
                }
                Object.assign(self.search, {
                    delimiter: candidateChar,
                    position: candidatePosition,
                    term: content.substring(candidatePosition + 1, selectionStart),
                });
                self.state.count++;
                return;
            }
            self.clearSearch();
        },
        fetch: {
            inProgress: false,
            rpcFunction: undefined,
        },
        insert(option) {
            const cursorPosition = comp.props.composer.selection.start;
            const content = comp.props.composer.textInputContent;
            let textLeft = content.substring(0, self.search.position + 1);
            let textRight = content.substring(cursorPosition, content.length);
            if (self.search.delimiter === ":") {
                textLeft = content.substring(0, self.search.position);
                textRight = content.substring(cursorPosition, content.length);
            }
            const recordReplacement = option.label;
            if (option.partner) {
                comp.props.composer.rawMentions.partnerIds.add(option.partner.id);
            }
            if (option.thread) {
                comp.props.composer.rawMentions.threadIds.add(option.thread.id);
            }
            if (option.cannedResponse) {
                comp.props.composer.cannedResponseIds.add(option.cannedResponse.id);
            }
            self.clearSearch();
            comp.props.composer.textInputContent = textLeft + recordReplacement + " " + textRight;
            comp.props.composer.selection.start = textLeft.length + recordReplacement.length + 1;
            comp.props.composer.selection.end = textLeft.length + recordReplacement.length + 1;
            comp.props.composer.forceCursorMove = true;
        },
        async process(func) {
            if (self.fetch.inProgress) {
                self.fetch.rpcFunction = func;
                return;
            }
            self.fetch.inProgress = true;
            self.fetch.rpcFunction = undefined;
            await func();
            self.fetch.inProgress = false;
            if (self.fetch.nextMentionRpcFunction) {
                self.process(self.fetch.nextMentionRpcFunction);
            }
        },
        search: {
            delimiter: undefined,
            position: undefined,
            term: undefined,
        },
        state: useState({
            count: 0,
            items: undefined,
        }),
        update() {
            if (!self.search.delimiter || !comp.props.composer.thread) {
                return;
            }
            const suggestions = suggestionService.searchSuggestions(
                self.search,
                { thread: comp.props.composer.thread },
                true
            );
            const { type, mainSuggestions, extraSuggestions = [] } = suggestions;
            if (!mainSuggestions.length && !extraSuggestions.length) {
                self.clearSearch();
                return;
            }
            // arbitrary limit to avoid displaying too many elements at once
            // ideally a load more mechanism should be introduced
            const limit = 8;
            mainSuggestions.length = Math.min(mainSuggestions.length, limit);
            extraSuggestions.length = Math.min(
                extraSuggestions.length,
                limit - mainSuggestions.length
            );
            self.state.items = { type, mainSuggestions, extraSuggestions };
        },
    };
    useEffect(
        () => {
            self.update();
            self.process(async () => {
                if (self.search.position === undefined || !self.search.delimiter) {
                    return; // ignore obsolete call
                }
                if (!comp.props.composer.thread) {
                    return;
                }
                await suggestionService.fetchSuggestions(self.search, {
                    thread: comp.props.composer.thread,
                    onFetched() {
                        if (owl.status(comp) === "destroyed") {
                            return;
                        }
                        self.update();
                    },
                });
                self.update();
            });
        },
        () => {
            return [self.search.delimiter, self.search.position, self.search.term];
        }
    );
    useEffect(
        () => {
            self.detect();
        },
        () => [
            comp.props.composer.selection.start,
            comp.props.composer.selection.end,
            comp.props.composer.textInputContent,
        ]
    );
    return self;
}
