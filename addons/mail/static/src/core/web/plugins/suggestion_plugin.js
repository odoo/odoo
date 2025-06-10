import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { rotate } from "@web/core/utils/arrays";
import { SuggestionList } from "../suggestion_list";
import { renderToElement } from "@web/core/utils/render";
import { rightPos } from "@html_editor/utils/position";
import { stateToUrl } from "@web/core/browser/router";
import { debounce } from "@web/core/utils/timing";
import { ConnectionAbortedError } from "@web/core/network/rpc";

export class SuggestionPlugin extends Plugin {
    static id = "suggestion";
    static dependencies = [
        "delete",
        "dom",
        "history",
        "input",
        "overlay",
        "selection",
        "userCommand",
    ];
    static shared = ["start"];
    resources = {
        input_handlers: this.onInput.bind(this),
        delete_handlers: this.detect.bind(this),
        post_undo_handlers: this.detect.bind(this),
        post_redo_handlers: this.detect.bind(this),
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.dependencies.overlay.createOverlay(SuggestionList);
        this.param = {
            delimiter: undefined,
            position: undefined,
            term: "",
        };
        this.lastFetchedSearch = undefined;
        this.searchState = reactive({
            count: 0,
            items: undefined,
            isFetching: false,
        });
        this.suggestionListState = reactive({});
        this.debouncedFetchSuggestions = debounce(this.fetchSuggestions.bind(this), 250);
        this.addDomListener(this.editable.ownerDocument, "keydown", this.onKeyDown);
    }

    get suggestionService() {
        return this.config.suggestionPLuginDependencies.suggestionService;
    }

    get isSearchMoreSpecificThanLastFetch() {
        return (
            this.lastFetchedSearch.delimiter === this.param.delimiter &&
            this.param.term.startsWith(this.lastFetchedSearch.term) &&
            this.lastFetchedSearch.position >= this.param.offset
        );
    }

    /** @returns {import("models").Composer} */
    get composer() {
        return this.config.suggestionPLuginDependencies.composer;
    }

    /** @returns {import("models").Thread} */
    get thread() {
        return this.composer?.thread || this.composer?.message?.thread;
    }

    onKeyDown(ev) {
        if (!this.overlay.isOpen) {
            return;
        }
        const key = ev.key;
        switch (key) {
            case "Escape":
                this.closeSuggestionList();
                break;
            case "Enter":
            case "Tab":
                ev.preventDefault();
                ev.stopImmediatePropagation();
                this.onSelected(
                    this.suggestionListState.type,
                    this.suggestionListState.suggestions[this.suggestionListState.currentIndex]
                );
                break;
            case "ArrowUp": {
                ev.preventDefault();
                this.suggestionListState.currentIndex = rotate(
                    this.suggestionListState.currentIndex,
                    this.suggestionListState.suggestions,
                    -1
                );
                ev.stopPropagation();
                break;
            }
            case "ArrowDown": {
                ev.preventDefault();
                this.suggestionListState.currentIndex = rotate(
                    this.suggestionListState.currentIndex,
                    this.suggestionListState.suggestions,
                    1
                );
                ev.stopPropagation();
                break;
            }
            case "ArrowLeft":
            case "ArrowRight": {
                this.closeSuggestionList();
                break;
            }
        }
    }

    onInput(ev) {
        const selection = this.dependencies.selection.getEditableSelection();
        const supportedDelimiters = this.suggestionService.getSupportedDelimiters(this.thread);
        const findAppropriateDelimiter = () => {
            for (const [delimiter, allowedPosition, minCharCountAfter] of supportedDelimiters) {
                const offset = selection.startOffset;
                if (offset - delimiter.length < 0) {
                    continue;
                }
                const candidateDelimiter = selection.startContainer.nodeValue?.slice(
                    offset - delimiter.length,
                    offset
                );
                if (
                    candidateDelimiter === delimiter &&
                    (allowedPosition === undefined || allowedPosition === offset - delimiter.length)
                ) {
                    const charBeforeCandidate = selection.startContainer.nodeValue?.slice(
                        offset - delimiter.length - 1,
                        offset - delimiter.length
                    );
                    if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                        continue;
                    }
                    this.minCharCountAfter = minCharCountAfter;
                    return delimiter;
                }
            }
            return false;
        };
        const candidateDelimiter = findAppropriateDelimiter();
        if (candidateDelimiter) {
            this.start(
                {
                    delimiter: candidateDelimiter,
                    term: "",
                },
                this.minCharCountAfter
            );
        } else {
            this.detect();
        }
    }

    start(param, minCharCountAfter) {
        const selection = this.dependencies.selection.getEditableSelection();
        this.offset = selection.startOffset;
        this.historySavePointRestore = this.dependencies.history.makeSavePoint();
        this.shouldUpdate = true;
        Object.assign(this.param, param);
        if (!minCharCountAfter) {
            this.openSuggestionList();
        }
    }

    openSuggestionList() {
        this.closeSuggestionList();
        const results = this.suggestionService.searchSuggestions(this.param, {
            thread: this.thread,
        });
        this.updateSuggestionList(results);
        this.fetch();
    }

    updateSuggestionList({ type, suggestions }) {
        Object.assign(this.suggestionListState, {
            type,
            suggestions,
            currentIndex: 0,
        });
        this.overlay.open({
            props: {
                document: this.document,
                close: () => this.overlay.close(),
                state: this.suggestionListState,
                onHovered: (currentIndex) => {
                    this.suggestionListState.currentIndex = currentIndex;
                },
                onSelected: this.onSelected.bind(this),
            },
        });
    }

    closeSuggestionList() {
        if (!this.overlay.isOpen) {
            return;
        }
        this.shouldUpdate = false;
        this.overlay.close();
    }

    detect() {
        if (!this.shouldUpdate) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        this.searchNode = selection.startContainer;
        const searchTerm = this.searchNode.nodeValue?.slice(this.offset, selection.endOffset);
        this.param.term = searchTerm;
        if (this.minCharCountAfter && this.param.term?.length < this.minCharCountAfter) {
            this.closeSuggestionList();
            this.shouldUpdate = true;
            return;
        }
        if (!this.isValidDetecting(selection)) {
            this.closeSuggestionList();
            this.clear();
            return;
        }
        this.search();
        this.fetch();
    }

    search() {
        const result = this.suggestionService.searchSuggestions(this.param, {
            thread: this.thread,
        });
        if (!result.suggestions?.length && !this.searchState.isFetching) {
            this.closeSuggestionList();
            this.shouldUpdate = true;
            return;
        }
        // arbitrary limit to avoid displaying too many elements at once
        // ideally a load more mechanism should be introduced
        const limit = 8;
        result.suggestions.length = Math.min(result.suggestions.length, limit);
        this.updateSuggestionList(result);
    }

    fetch() {
        if (!this.param.delimiter) {
            return; // nothing else to fetch
        }
        if (this.composer && this.composer.store.self.type !== "partner") {
            return; // guests cannot access fetch suggestion method
        }
        if (
            this.lastFetchedSearch?.count === 0 &&
            (!this.param.delimiter || this.isSearchMoreSpecificThanLastFetch)
        ) {
            return; // no need to fetch since this is more specific than last and last had no result
        }
        this.debouncedFetchSuggestions();
    }

    async fetchSuggestions() {
        let resetFetchingState = true;
        try {
            this.abortController?.abort();
            this.abortController = new AbortController();
            this.searchState.isFetching = true;
            await this.suggestionService.fetchSuggestions(this.param, {
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
                this.searchState.isFetching = false;
            }
        }
        const results = this.search();
        this.lastFetchedSearch = {
            ...this.param,
            count: results?.length ?? 0,
        };
    }

    isValidDetecting(selection) {
        return (
            selection.endContainer === this.searchNode &&
            this.searchNode.nodeValue?.slice(
                this.offset - this.param.delimiter?.length,
                this.offset
            ) === this.param.delimiter &&
            selection.endOffset >= this.offset
        );
    }

    clear() {
        Object.assign(this.param, {
            delimiter: undefined,
            position: undefined,
            term: "",
        });
    }

    insert(type, option) {
        if (type === "Partner") {
            if (option.isSpecial) {
                const partnerBlock = renderToElement("mail.Suggestion.Special", {
                    label: option.label,
                });
                this.dependencies.dom.insert(partnerBlock);
                const [anchorNode, anchorOffset] = rightPos(partnerBlock);
                this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
                this.dependencies.dom.insert("\u00A0");
                return;
            }
            if (option.Model._name === "res.role") {
                this.composer?.mentionedRoles.add({ id: option.id });
                const roleBlock = renderToElement("mail.Suggestion.Role", {
                    href: stateToUrl({ model: "res.role", resId: option.id }),
                    roleId: option.id,
                    displayName: option.name,
                });
                this.dependencies.dom.insert(roleBlock);
                const [anchorNode, anchorOffset] = rightPos(roleBlock);
                this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
                this.dependencies.dom.insert("\u00A0");
                return;
            }
            this.composer?.mentionedPartners.add({
                id: option.id,
                type: "partner",
            });
            const partnerBlock = renderToElement("mail.Suggestion.Partner", {
                href: stateToUrl({ model: "res.partner", resId: option.id }),
                partnerId: option.id,
                displayName: option.name,
            });
            this.dependencies.dom.insert(partnerBlock);
            const [anchorNode, anchorOffset] = rightPos(partnerBlock);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
            this.dependencies.dom.insert("\u00A0");
        }
        if (type === "Thread") {
            this.composer?.mentionedChannels.add({
                model: "discuss.channel",
                id: option.id,
            });
            let className, text;
            if (option.parent_channel_id) {
                className = "o_channel_redirect o_channel_redirect_asThread";
                text = `#${option.parent_channel_id.displayName}` + " > " + `${option.displayName}`;
            } else {
                className = "o_channel_redirect";
                text = `#${option.displayName}`;
            }
            const threadBlock = renderToElement("mail.Suggestion.Thread", {
                href: stateToUrl({ model: "discuss.channel", resId: option.id }),
                threadId: option.id,
                displayName: text,
                className,
            });
            this.dependencies.dom.insert(threadBlock);
            const [anchorNode, anchorOffset] = rightPos(threadBlock);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
            this.dependencies.dom.insert("\u00A0");
        }
        if (type === "CannedResponse") {
            this.composer?.cannedResponses.push(option);
            this.dependencies.dom.insert(option.substitution);
            this.dependencies.dom.insert("\u00A0");
        }
        if (type === "Emoji") {
            this.dependencies.dom.insert(option.codepoints);
            this.dependencies.dom.insert("\u00A0");
        }
        if (type === "ChannelCommand") {
            this.dependencies.dom.insert("/" + option.name);
            this.dependencies.dom.insert("\u00A0");
        }
    }

    onSelected(type, option) {
        this.historySavePointRestore();
        if (this.param.delimiter === "::") {
            // remove extra colon from the left of the cursor
            this.dependencies.delete.delete("backward", "character");
            this.dependencies.delete.delete("backward", "character");
        } else {
            this.dependencies.delete.delete("backward", "character");
        }
        this.insert(type, option);
        this.dependencies.history.addStep();
        this.closeSuggestionList();
        this.clear();
        this.dependencies.selection.focusEditable();
    }
}
