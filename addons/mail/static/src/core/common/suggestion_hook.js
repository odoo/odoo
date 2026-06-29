import { useComponent, useLayoutEffect } from "@web/owl2/utils";
import { isContentEditable, isTextNode } from "@html_editor/utils/dom_info";
import { rightPos } from "@html_editor/utils/position";
import {
    generatePartnerMentionElement,
    generateRoleMentionElement,
    generateSpecialMentionElement,
} from "@mail/utils/common/format";
import { proxy, status, t } from "@odoo/owl";
import { emojiType } from "@web/core/emoji_picker/emoji_loader";
import { ConnectionAbortedError } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { useSearch } from "@mail/utils/common/hooks";

/**
 * Delimiters that trigger suggestion lists in the composer.
 *
 * @typedef {typeof SUGGESTION_DELIMITERS[keyof typeof SUGGESTION_DELIMITERS]} SuggestionDelimiter
 */
export const SUGGESTION_DELIMITERS = Object.freeze({
    PARTNER: "@",
    CANNED_RESPONSE: "::",
    EMOJI: ":",
    CHANNEL_COMMAND: "/",
});

/** @param {import("models").Store} store */
export const optionType = (store) =>
    t.object({
        buttonClass: t.string().optional(),
        cannedResponse: t.instanceOf(store["mail.canned.response"].Class).optional(),
        classList: t.string().optional(),
        emoji: emojiType.optional(),
        group: t.any().optional(),
        help: t.string().optional(),
        isSpecial: t.boolean().optional(),
        label: t.string().optional(),
        optionTemplate: t.string().optional(),
        partner: t.instanceOf(store["res.partner"].Class).optional(),
        role: t.instanceOf(store["res.role"].Class).optional(),
        source: t.string().optional(),
        thread: t.instanceOf(store["mail.thread"].Class).optional(),
        title: t.string().optional(),
        unselectable: t.boolean().optional(),
    });

/** @typedef {import("@odoo/owl").StripType<ReturnType<typeof optionType>>} Option */

/**
 * @typedef {import("models").ResPartner
 *   | import("models").ResRole
 *   | import("models").CannedResponse
 *   | import("@web/core/emoji_picker/emoji_picker").Emoji
 *   | import("@mail/core/common/store_service").SpecialMention} Suggestion
 */

export class UseSuggestion {
    constructor(comp) {
        this.comp = comp;
        this.suggestionService = useService("mail.suggestion");
        this.detection = proxy({
            /** @type {SuggestionDelimiter|undefined} */
            delimiter: undefined,
            /** @type {number|undefined} */
            position: undefined,
            term: "",
        });
        this.search = useSearch({
            fetch: this.fetchSuggestions.bind(this),
            filter: this.update.bind(this),
            deps: () => [this.detection.delimiter, this.detection.position],
            isActive: () => !!this.detection.delimiter,
        });
        useLayoutEffect(
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
    clearRawMentions() {
        this.composer.mentionedPartners.length = 0;
        this.composer.mentionedRoles.length = 0;
    }
    clearCannedResponses() {
        this.composer.cannedResponses = [];
    }
    clearSearch() {
        Object.assign(this.detection, {
            delimiter: undefined,
            position: undefined,
            term: "",
        });
        this.search.reset();
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
        if (this.detection.position !== undefined && this.detection.position < start) {
            candidatePositions.push(this.detection.position);
        }
        const supportedDelimiters = this.suggestionService.getSupportedDelimiters(
            this.thread,
            this.comp
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
            Object.assign(this.detection, {
                delimiter: candidateDelimiter,
                position: candidatePosition,
                term: text.substring(candidatePosition + candidateDelimiter.length, start),
            });
            this.search.searchTerm = this.detection.term;
            return;
        }
        this.clearSearch();
    }
    get thread() {
        return this.composer.thread || this.composer.message?.thread;
    }
    insert(option) {
        let position = this.detection.position + 1;
        if (
            [SUGGESTION_DELIMITERS.EMOJI, SUGGESTION_DELIMITERS.CANNED_RESPONSE].includes(
                this.detection.delimiter
            ) ||
            (this.comp.composerService.htmlEnabled &&
                this.detection.delimiter !== SUGGESTION_DELIMITERS.CHANNEL_COMMAND)
        ) {
            position = this.detection.position;
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
        } else if (option.cannedResponse) {
            this.composer.cannedResponses.push(option.cannedResponse);
        }
        if (this.comp.composerService.htmlEnabled) {
            const inlineElement = makeMentionFromOption(option, { thread: this.thread });
            this.comp.editor.shared.dom.insert(inlineElement);
            const [anchorNode, anchorOffset] = rightPos(inlineElement);
            this.comp.editor.shared.selection.setSelection({ anchorNode, anchorOffset });
            this.comp.editor.shared.dom.insert("\u00A0");
            this.comp.editor.shared.history.commit();
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
        if (!this.detection.delimiter) {
            return undefined;
        }
        const { type, suggestions } = this.suggestionService.searchSuggestions(this.detection, {
            composerType: this.comp.props.type,
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

    async fetchSuggestions() {
        if (!this.thread || status(this.comp) === "destroyed") {
            return;
        }
        if (!this.composer.store.self_user) {
            return; // guests cannot access fetch suggestion method
        }
        try {
            this.abortController?.abort();
            this.abortController = new AbortController();
            await this.suggestionService.fetchSuggestions(this.detection, {
                thread: this.thread,
                abortSignal: this.abortController.signal,
                composerType: this.comp.props.type,
            });
        } catch (e) {
            if (e instanceof ConnectionAbortedError) {
                return;
            }
            throw e;
        }
        if (!this.thread || status(this.comp) === "destroyed") {
            return;
        }
        const { suggestions } = this.suggestionService.searchSuggestions(this.detection, {
            thread: this.thread,
        });
        return suggestions.length === 0 ? false : undefined;
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
                        label:
                            thread?.getPersonaName(suggestion) ||
                            suggestion.displayName ||
                            suggestion.email ||
                            "",
                        partner: suggestion,
                        thread,
                        classList,
                    };
                }),
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
    } else {
        inlineElement = document.createTextNode(option.label);
    }
    return inlineElement;
}
