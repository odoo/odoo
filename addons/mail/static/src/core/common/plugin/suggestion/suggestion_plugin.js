import { Plugin } from "@html_editor/plugin";
import { getDeepestPosition, isContentEditable, isTextNode } from "@html_editor/utils/dom_info";
import { rightPos } from "@html_editor/utils/position";

import { NavigableList } from "@mail/core/common/navigable_list";
import { useSearch } from "@mail/utils/common/hooks";

import { markRaw, proxy, untrack, useOnChange } from "@odoo/owl";

import { normalize } from "@web/core/l10n/utils";
import { ConnectionAbortedError } from "@web/core/network/rpc";

/** @typedef {import("@mail/core/common/navigable_list").Option} Option */

/**
 * @typedef {Object} SuggestionSource
 * @property {number} [allowedPosition] the only position of the delimiter in its text node
 * @property {string} delimiter
 * @property {(cleanedTerm: string, options: { abortSignal: AbortSignal }) => Promise<void>} [fetch]
 * @property {() => boolean} [isAvailable]
 * @property {boolean} [keepsDelimiter] whether the suggestion is inserted after the delimiter
 * @property {(cleanedTerm: string) => Object[]} search
 * @property {(option: Option) => Node} [toNode] the inserted node, a text of the label by default
 * @property {(suggestions: Object[]) => { optionTemplate?: string, options: Option[] }} toOptions
 */

/** @typedef {SuggestionSource[]} suggestion_sources */

/** Suggests what can follow a delimiter typed in the editable (e.g. `@` for a partner). */
export class MailSuggestionPlugin extends Plugin {
    static id = "suggestion";
    static dependencies = ["dom", "history", "overlay", "selection"];
    static shared = ["getSources", "hasSuggestions"];
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
     *   getSuggestionPosition?: () => string,
     *   getSuggestionTarget?: () => HTMLElement|null,
     *   onInsertSuggestion?: (option: Option) => void,
     * }}
     */
    deps;
    /** @type {{ position: number|undefined, source: SuggestionSource|undefined }} */
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
        this.detection = proxy({ position: undefined, source: undefined });
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
                    position: this.deps.getSuggestionPosition?.() ?? "bottom-start",
                    rememberPosition: false,
                },
            },
            { rootId: this.editable.getRootNode()?.host?.id }
        );
        this.search = useSearch({
            fetch: this.fetchSuggestions.bind(this),
            filter: this.update.bind(this),
            deps: () => [this.detection.source, this.detection.position],
            isActive: () => !!this.detection.source,
        });
        useOnChange(
            () => [this.search.results, this.search.loading, this.search.searchTerm],
            (results, loading, searchTerm) => {
                const { optionTemplate, options } = results?.source
                    ? results.source.toOptions(results.suggestions)
                    : { options: [] };
                // raw: the list sorts its options in place while rendering
                Object.assign(this.listProps, {
                    isLoading: !!searchTerm && loading,
                    options: markRaw(
                        options.map((option) => ({
                            ...option,
                            classList: "o-mail-Composer-suggestion",
                        }))
                    ),
                    optionTemplate,
                });
            }
        );
    }

    clearSearch() {
        Object.assign(this.detection, { position: undefined, source: undefined });
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
        const sources = this.getSources();
        for (const candidatePosition of candidatePositions) {
            if (candidatePosition < 0 || candidatePosition >= text.length) {
                continue;
            }

            const findAppropriateSource = () => {
                let goodCandidate;
                for (const source of sources) {
                    const { allowedPosition, delimiter } = source;
                    if (
                        text.substring(candidatePosition).startsWith(delimiter) && // delimiter is used
                        (allowedPosition === undefined || allowedPosition === candidatePosition) && // delimiter is allowed position
                        (!goodCandidate || delimiter.length > goodCandidate.delimiter.length) // delimiter is more specific
                    ) {
                        goodCandidate = source;
                    }
                }
                return goodCandidate;
            };

            const candidateSource = findAppropriateSource();
            if (!candidateSource) {
                continue;
            }
            const charBeforeCandidate = text[candidatePosition - 1];
            if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                continue;
            }
            Object.assign(this.detection, { position: candidatePosition, source: candidateSource });
            this.search.searchTerm = text.substring(
                candidatePosition + candidateSource.delimiter.length,
                start
            );
            this.overlay.open({ target: this.deps.getSuggestionTarget?.(), props: this.listProps });
            return;
        }
        this.clearSearch();
    }

    dismiss() {
        this.isDismissed = true;
    }

    /** @param {string} term */
    async fetchSuggestions(term) {
        if (this.isDestroyed) {
            return;
        }
        const { source } = this.detection;
        try {
            this.abortController?.abort();
            this.abortController = new AbortController();
            await source.fetch?.(normalize(term), { abortSignal: this.abortController.signal });
        } catch (e) {
            if (e instanceof ConnectionAbortedError) {
                return;
            }
            throw e;
        }
        if (this.isDestroyed) {
            return;
        }
        return this.searchSuggestions(term).length === 0 ? false : undefined;
    }

    /**
     * Programmatic insertions (e.g. canned response button) may leave the
     * cursor between nodes rather than inside a text node.
     */
    getCursorPosition() {
        const { endContainer, endOffset } = this.dependencies.selection.getEditableSelection();
        return getDeepestPosition(endContainer, endOffset);
    }

    getSources() {
        return this.getResource("suggestion_sources").filter(
            (source) => source.isAvailable?.() ?? true
        );
    }

    hasSuggestions() {
        return Boolean(this.search.results);
    }

    /** @param {Option} option */
    insert(option) {
        const { position: delimiterPosition, source } = this.detection;
        if (!source) {
            return;
        }
        const position = source.keepsDelimiter
            ? delimiterPosition + source.delimiter.length
            : delimiterPosition;
        const [node, offset] = this.getCursorPosition();
        this.dependencies.selection.setSelection({
            anchorNode: node,
            anchorOffset: position,
            focusNode: node,
            focusOffset: offset,
        });
        this.deps.onInsertSuggestion?.(option);
        const inlineElement = source.toNode?.(option) ?? this.document.createTextNode(option.label);
        this.dependencies.dom.insert(inlineElement);
        const [anchorNode, anchorOffset] = rightPos(inlineElement);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        this.dependencies.dom.insert("\u00A0");
        this.dependencies.history.commit();
    }

    /** @param {string} term */
    searchSuggestions(term) {
        return this.detection.source?.search(normalize(term)) ?? [];
    }

    /** @param {string} term */
    update(term) {
        const { source } = this.detection;
        if (!source) {
            return undefined;
        }
        if (this.isDismissed) {
            return this.search.results;
        }
        const suggestions = this.searchSuggestions(term);
        if (!suggestions.length) {
            return undefined;
        }
        // arbitrary limit to avoid displaying too many elements at once
        // ideally a load more mechanism should be introduced
        const limit = 8;
        return { source, suggestions: suggestions.slice(0, limit) };
    }
}
