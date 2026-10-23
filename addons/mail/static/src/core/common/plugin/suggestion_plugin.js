import { Plugin } from "@html_editor/plugin";
import { getDeepestPosition, isContentEditable, isTextNode } from "@html_editor/utils/dom_info";
import { rightPos } from "@html_editor/utils/position";

import { NavigableList } from "@mail/core/common/navigable_list";
import {
    generatePartnerMentionElement,
    generateRoleMentionElement,
    generateSpecialMentionElement,
} from "@mail/utils/common/format";
import { useSearch } from "@mail/utils/common/hooks";

import { markRaw, proxy, untrack, useOnChange } from "@odoo/owl";

import { ConnectionAbortedError } from "@web/core/network/rpc";

/**
 * Delimiters that trigger suggestion lists in the composer.
 *
 * @typedef {typeof SUGGESTION_DELIMITERS[keyof typeof SUGGESTION_DELIMITERS]} SuggestionDelimiter
 */
export const SUGGESTION_DELIMITERS = Object.freeze({
    PARTNER: "@",
    CANNED_RESPONSE: "::",
    CHANNEL_COMMAND: "/",
});

/** @typedef {import("@mail/core/common/navigable_list").Option} Option */

/**
 * @typedef {import("models").ResPartner
 *   | import("models").ResRole
 *   | import("models").CannedResponse
 *   | import("@mail/core/common/store_plugin").SpecialMention} Suggestion
 */

/**
 * Maps raw suggestion records to navigable list option objects for all suggestion types.
 *
 * @param {string} type
 * @param {Suggestion[]} suggestions
 * @param {Object} [params]
 * @param {import("models").Thread} [params.thread] The thread where the suggestion is being
 *   composed. Used e.g. to resolve partner display names in context and stored on the resulting
 *   Option so that consumers (insertion handlers, mention templates) can access it.
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
                        label: (
                            thread?.getPersonaName(suggestion) ||
                            suggestion.displayName ||
                            suggestion.email ||
                            ""
                        ).trim(),
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

/** Suggests what can follow a delimiter typed in the editable (e.g. `@` for a partner). */
export class MailSuggestionPlugin extends Plugin {
    static id = "suggestion";
    static dependencies = ["dom", "history", "overlay", "selection"];
    static shared = ["hasSuggestions"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        on_committed_to_history_handlers: () => {
            if (this.isAttached) {
                untrack(() => this.detect());
            }
        },
        on_editor_started_handlers: () => Promise.resolve().then(() => (this.isAttached = true)),
        on_selectionchange_handlers: ({ documentSelectionIsInEditable }) => {
            if (documentSelectionIsInEditable) {
                // Moving the cursor changes the suggestion being typed.
                this.detect();
            }
        },
    };

    /** @type {AbortController|undefined} */
    abortController;
    /**
     * @type {{
     *   getAncestors: () => Readonly<Record<string, any>>,
     *   getComposerType: () => "message"|"note"|false|undefined,
     *   getSuggestionPosition: () => string,
     *   getSuggestionTarget: () => HTMLElement|null,
     *   getThread: () => import("models").Thread|null,
     *   onInsertSuggestion: (option: Option) => void,
     * }}
     */
    deps;
    /** @type {{ delimiter: SuggestionDelimiter|undefined, position: number|undefined, term: string }} */
    detection;
    /** Set after the attachment, whose commits come from the initial content, not from typing. */
    isAttached = false;
    /**
     * Whether the user closed the suggestion list. Only the answer of an ongoing fetch is
     * dropped: a new user input searches and opens the list again.
     */
    isDismissed = false;
    /**
     * @type {{
     *   class: string,
     *   isLoading: boolean,
     *   onClose: () => void,
     *   onSelect: (ev: Event, option: Option) => void,
     *   options: Option[],
     *   optionTemplate: string|undefined,
     * }}
     */
    listProps;
    /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
    overlay;
    /** @type {import("@mail/utils/common/hooks").SearchState} */
    search;

    setup() {
        this.deps = this.config.composerPluginDependencies;
        this.detection = proxy({ delimiter: undefined, position: undefined, term: "" });
        this.listProps = proxy({
            class: "o-mail-Composer-suggestionList",
            isLoading: false,
            onClose: () => this.dismiss(),
            onSelect: (ev, option) => this.insert(option),
            options: [],
            optionTemplate: undefined,
        });
        this.overlay = this.dependencies.overlay.createOverlay(
            NavigableList,
            {
                closeOnPointerdown: false,
                positionOptions: {
                    // not the editable's scroll container, which is inside the target
                    container: this.document.documentElement,
                    position: this.deps.getSuggestionPosition(),
                    rememberPosition: false,
                },
            },
            { rootId: this.editable.getRootNode()?.host?.id }
        );
        this.search = useSearch({
            fetch: this.fetchSuggestions.bind(this),
            filter: this.update.bind(this),
            deps: () => [this.detection.delimiter, this.detection.position],
            isActive: () => !!this.detection.delimiter,
        });
        useOnChange(
            () => [this.search.results, this.search.loading, this.search.searchTerm],
            (results, loading, searchTerm) => {
                const { optionTemplate, options } = results
                    ? mapSuggestionsToOptions(results.type, results.suggestions, {
                          thread: this.deps.getThread(),
                      })
                    : { options: [] };
                // raw: the list sorts its options in place while rendering
                Object.assign(this.listProps, {
                    isLoading: !!searchTerm && loading,
                    options: markRaw(options),
                    optionTemplate,
                });
            }
        );
    }

    clearSearch() {
        Object.assign(this.detection, {
            delimiter: undefined,
            position: undefined,
            term: "",
        });
        this.search.reset();
        if (this.overlay.isOpen) {
            this.overlay.close();
        }
    }

    detect() {
        this.isDismissed = false;
        const selection = this.dependencies.selection.getEditableSelection();
        if (!selection.isCollapsed) {
            // avoid interfering with multi-char selection
            this.clearSearch();
            return;
        }
        const [node, start] = this.getCursorPosition();
        if (!isTextNode(node) || !isContentEditable(node)) {
            this.clearSearch();
            return;
        }
        const text = node.textContent;
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
        const supportedDelimiters = this.services["mail.suggestion"].getSupportedDelimiters(
            this.deps.getThread(),
            this.deps.getAncestors()
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
            this.overlay.open({ target: this.deps.getSuggestionTarget(), props: this.listProps });
            return;
        }
        this.clearSearch();
    }

    dismiss() {
        this.isDismissed = true;
    }

    async fetchSuggestions() {
        const thread = this.deps.getThread();
        if (!thread || this.isDestroyed) {
            return;
        }
        if (!this.services["mail.store"].self_user) {
            return; // guests cannot access fetch suggestion method
        }
        const composerType = this.deps.getComposerType();
        try {
            this.abortController?.abort();
            this.abortController = new AbortController();
            await this.services["mail.suggestion"].fetchSuggestions(this.detection, {
                thread,
                abortSignal: this.abortController.signal,
                composerType,
            });
        } catch (e) {
            if (e instanceof ConnectionAbortedError) {
                return;
            }
            throw e;
        }
        if (!this.deps.getThread() || this.isDestroyed) {
            return;
        }
        const { suggestions } = this.services["mail.suggestion"].searchSuggestions(this.detection, {
            thread: this.deps.getThread(),
        });
        return suggestions.length === 0 ? false : undefined;
    }

    /**
     * Programmatic insertions (e.g. canned response button) may leave the
     * cursor between nodes rather than inside a text node.
     */
    getCursorPosition() {
        const { endContainer, endOffset } = this.dependencies.selection.getEditableSelection();
        return getDeepestPosition(endContainer, endOffset);
    }

    hasSuggestions() {
        return Boolean(this.search.results);
    }

    /** @param {Option} option */
    insert(option) {
        const position =
            this.detection.delimiter === SUGGESTION_DELIMITERS.CHANNEL_COMMAND
                ? this.detection.position + 1
                : this.detection.position;
        const [node, offset] = this.getCursorPosition();
        this.dependencies.selection.setSelection({
            anchorNode: node,
            anchorOffset: position,
            focusNode: node,
            focusOffset: offset,
        });
        this.deps.onInsertSuggestion(option);
        const inlineElement = makeMentionFromOption(option, { thread: this.deps.getThread() });
        this.dependencies.dom.insert(inlineElement);
        const [anchorNode, anchorOffset] = rightPos(inlineElement);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        this.dependencies.dom.insert("\u00A0");
        this.dependencies.history.commit();
    }

    update() {
        if (!this.detection.delimiter) {
            return undefined;
        }
        if (this.isDismissed) {
            return this.search.results;
        }
        const { type, suggestions } = this.services["mail.suggestion"].searchSuggestions(
            this.detection,
            { composerType: this.deps.getComposerType(), thread: this.deps.getThread() }
        );
        if (!suggestions.length) {
            return undefined;
        }
        // arbitrary limit to avoid displaying too many elements at once
        // ideally a load more mechanism should be introduced
        const limit = 8;
        suggestions.length = Math.min(suggestions.length, limit);
        return { type, suggestions };
    }
}
