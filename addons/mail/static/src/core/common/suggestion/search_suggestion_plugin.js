import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { useSequential } from "@mail/utils/common/hooks";

export class SearchSuggestionPlugin extends Plugin {
    static id = "searchSuggestion";
    static dependencies = ["suggestion", "selection", "dom", "history"];
    resources = {
        beforeinput_handlers: this.onBeforeInput.bind(this),
        input_handlers: this.onInput.bind(this),
        delete_handlers: this.detect.bind(this),
        post_undo_handlers: this.detect.bind(this),
        post_redo_handlers: this.detect.bind(this),
    };

    setup() {
        this.supportedDelimiters = this.getResource("supported_delimiters");
        this.sequential = useSequential();
        this.state = reactive({
            count: 0,
            isFetching: false,
        });
        this.param = {
            delimiter: undefined,
            term: "",
        };
        this.lastFetchedSearch = undefined;
    }

    get isSearchMoreSpecificThanLastFetch() {
        return this.param.term.startsWith(this.lastFetchedSearch.term);
    }

    get thread() {
        const composer = this.config.mailServices.composer;
        return composer.thread || composer.message.thread;
    }

    onBeforeInput(ev) {
        const char = ev.data;
        if (this.supportedDelimiters.includes(char)) {
            this.historySavePointRestore = this.dependencies.history.makeSavePoint();
        }
    }

    onInput(ev) {
        const char = ev.data;
        if (this.supportedDelimiters.includes(char)) {
            this.param.delimiter = char;
            this.start();
        } else {
            this.detect();
        }
    }

    start() {
        const selection = this.dependencies.selection.getEditableSelection();
        this.offset = selection.startOffset - 1;
        const results = this.dependencies.suggestion.search(
            { delimiter: this.param.delimiter, term: "" },
            { thread: this.thread }
        );
        this.dependencies.suggestion.open({
            suggestions: results,
            categories: this.categories,
            onApplySuggestion: (option) => {
                this.historySavePointRestore();
                this.dependencies.suggestion.insert(option);
                this.dependencies.history.addStep();
                this.clear();
            },
            onClose: () => {
                this.shouldUpdate = false;
            },
        });
        this.shouldUpdate = true;
    }

    detect() {
        if (!this.shouldUpdate) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        this.searchNode = selection.startContainer;
        if (!this.isSearching(selection)) {
            this.dependencies.suggestion.close();
            this.clear();
            return;
        }
        const searchTerm = this.searchNode.nodeValue.slice(this.offset + 1, selection.endOffset);
        if (searchTerm.includes(" ")) {
            this.dependencies.suggestion.close();
            return;
        }
        this.param.term = searchTerm;
        this.update();
        this.sequential(async () => {
            if (this.param.term !== searchTerm) {
                return; // ignore obsolete call
            }
            if (this.lastFetchedSearch?.count === 0 && this.isSearchMoreSpecificThanLastFetch) {
                return; // no need to fetch since this is more specific than last and last had no result
            }
            this.state.isFetching = true;
            try {
                await this.dependencies.suggestion.fetch(this.param, {
                    thread: this.thread,
                });
            } catch {
                this.lastFetchedSearch = null;
            } finally {
                this.state.isFetching = false;
            }
            const results = this.update();
            this.lastFetchedSearch = {
                ...this.param,
                count: results?.length ?? 0,
            };
            if (this.param.term === searchTerm && !results?.length) {
                this.clear();
            }
        });
    }

    update() {
        // if (!this.search.delimiter) {
        //     return;
        // }
        const suggestions = this.dependencies.suggestion.search(this.param, {
            thread: this.thread,
            sort: true,
        });
        console.log(suggestions);
        if (!suggestions.length) {
            this.dependencies.suggestion.close();
            return;
        }
        // arbitrary limit to avoid displaying too many elements at once
        // ideally a load more mechanism should be introduced
        const limit = 8;
        suggestions.length = Math.min(suggestions.length, limit);
        this.dependencies.suggestion.update(suggestions);
        return suggestions;
    }

    isSearching(selection) {
        return (
            selection.endContainer === this.searchNode &&
            this.searchNode.nodeValue &&
            this.searchNode.nodeValue[this.offset] === this.param.delimiter &&
            selection.endOffset >= this.offset
        );
    }

    clear() {
        Object.assign(this.param, {
            delimiter: undefined,
            term: "",
        });
    }
}
