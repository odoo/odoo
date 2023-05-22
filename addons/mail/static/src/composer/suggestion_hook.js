/* @odoo-module */

import { useComponent, useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { generateMentionLink } from "@mail/utils/format";
import { setCursorEnd } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

export function useSuggestion() {
    const comp = useComponent();
    /** @type {import("@mail/composer/suggestion_service").SuggestionService} */
    const suggestionService = useService("mail.suggestion");
    const self = {
        clearRawMentions() {
            comp.props.composer.rawMentions.partnerIds.length = 0;
            comp.props.composer.rawMentions.threadIds.length = 0;
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
            const range = comp.props.composer.range;
            if (!range) {
                return;
            }
            if (!range?.collapsed) {
                // avoid interfering with multi-char selection
                self.clearSearch();
            }
            const candidateRanges = [];
            // keep the current delimiter if it is still valid
            if (self.search.position !== undefined) {
                candidateRanges.push(self.search.position);
            }
            // consider the char before the current cursor position if the
            // current delimiter is no longer valid (or if there is none)
            if (range.startOffset > 0) {
                candidateRanges.push(range);
            }
            const supportedDelimiters = suggestionService.getSupportedDelimiters(
                comp.props.composer.thread
            );
            const content = range.startContainer.textContent;
            for (const candidateRange of candidateRanges) {
                const candidateChar = content[candidateRange.startOffset - 1];
                if (
                    !supportedDelimiters.find(
                        ([delimiter, allowedPosition]) =>
                            delimiter === candidateChar &&
                            (allowedPosition === undefined ||
                                allowedPosition === candidateRange.startOffset - 1)
                    )
                ) {
                    continue;
                }
                const charBeforeCandidate = content[candidateRange.startOffset - 2];
                if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                    continue;
                }
                Object.assign(self.search, {
                    delimiter: candidateChar,
                    position: candidateRange,
                    term: content.substring(candidateRange.startOffset, range.startOffset),
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
        insert(option, callback = () => {}) {
            const wysiwyg = comp.wysiwyg;
            let recordReplacement = option.label;
            if (option.partner) {
                comp.props.composer.rawMentions.partnerIds.add(option.partner.id);
                recordReplacement = "@" + recordReplacement;
            }
            if (option.thread) {
                comp.props.composer.rawMentions.threadIds.add(option.thread.id);
                recordReplacement = "#" + recordReplacement;
            }
            if (option.help) {
                recordReplacement = "/" + recordReplacement;
            }
            const replaceRange = new Range();
            replaceRange.setStart(
                self.search.position.startContainer,
                self.search.position.startOffset - 1
            );
            replaceRange.setEnd(
                comp.props.composer.range.startContainer,
                comp.props.composer.range.startOffset
            );
            wysiwyg.odooEditor.historyPauseSteps();
            replaceRange.deleteContents();
            if (option.partner || option.thread) {
                const link = document.createElement("a");
                link.textContent = recordReplacement;
                const attrs = generateMentionLink({
                    partner: option.partner,
                    thread: option.thread,
                });
                for (const [key, value] of Object.entries(attrs)) {
                    link.setAttribute(key, value);
                }
                self.search.position.insertNode(link);
                const space = document.createTextNode("\u00A0");
                link.parentNode.insertBefore(space, link.nextSibling);
                setCursorEnd(space);
            } else {
                const text = document.createTextNode(recordReplacement + "\u00A0");
                self.search.position.insertNode(text);
                setCursorEnd(text);
            }
            wysiwyg.odooEditor.historyUnpauseSteps();
            wysiwyg.odooEditor.historyStep();
            self.clearSearch();
            callback();
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
        () => [comp.props.composer.wysiwygValue, comp.props.composer.range]
    );
    return self;
}
