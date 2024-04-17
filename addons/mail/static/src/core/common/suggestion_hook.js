/* @odoo-module */

import { useSequential } from "@mail/utils/common/hooks";
import { status, useComponent, useEffect, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export function useSuggestion() {
    const comp = useComponent();
    const sequential = useSequential();
    const suggestionService = useService("mail.suggestion");
    const self = {
        clearRawMentions() {
            comp.props.composer.mentionedChannels.length = 0;
            comp.props.composer.mentionedPartners.length = 0;
        },
        clearCannedResponses() {
            comp.props.composer.cannedResponses = [];
        },
        clearSearch() {
            Object.assign(self.search, {
                delimiter: undefined,
                position: undefined,
                term: "",
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
                return;
            }
            const candidatePositions = [];
            // consider the chars before the current cursor position
            let numberOfSpaces = 0;
            for (let index = selectionStart - 1; index >= 0; --index) {
                if (/\s/.test(content[index])) {
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
            if (self.search.position !== undefined && self.search.position < selectionStart) {
                candidatePositions.push(self.search.position);
            }
            const supportedDelimiters = suggestionService.getSupportedDelimiters(self.thread);
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
        get thread() {
            return comp.props.composer.thread || comp.props.composer.message.originThread;
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
                comp.props.composer.mentionedPartners.add({
                    id: option.partner.id,
                    type: "partner",
                });
            }
            if (option.thread) {
                comp.props.composer.mentionedChannels.add({
                    model: "discuss.channel",
                    id: option.thread.id,
                });
            }
            if (option.cannedResponse) {
                comp.props.composer.cannedResponses.push(option.cannedResponse);
            }
            self.clearSearch();
            comp.props.composer.textInputContent = textLeft + recordReplacement + " " + textRight;
            comp.props.composer.selection.start = textLeft.length + recordReplacement.length + 1;
            comp.props.composer.selection.end = textLeft.length + recordReplacement.length + 1;
            comp.props.composer.forceCursorMove = true;
        },
        search: {
            delimiter: undefined,
            position: undefined,
            term: "",
        },
        state: useState({
            count: 0,
            items: undefined,
        }),
        update() {
            if (!self.search.delimiter) {
                return;
            }
            const suggestions = suggestionService.searchSuggestions(self.search, {
                thread: self.thread,
                sort: true,
            });
            const { type, mainSuggestions, extraSuggestions = [] } = suggestions;
            if (!mainSuggestions.length && !extraSuggestions.length) {
                self.state.items = undefined;
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
        (delimiter, position, term) => {
            self.update();
            if (self.search.position === undefined || !self.search.delimiter) {
                return; // nothing else to fetch
            }
            sequential(async () => {
                if (
                    self.search.delimiter !== delimiter ||
                    self.search.position !== position ||
                    self.search.term !== term
                ) {
                    return; // ignore obsolete call
                }
                await suggestionService.fetchSuggestions(self.search, {
                    thread: self.thread,
                });
                if (status(comp) === "destroyed") {
                    return;
                }
                self.update();
                if (
                    self.search.delimiter === delimiter &&
                    self.search.position === position &&
                    self.search.term === term &&
                    !self.state.items?.mainSuggestions.length &&
                    !self.state.items?.extraSuggestions.length
                ) {
                    self.clearSearch();
                }
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
