import { Plugin } from "@html_editor/plugin";
// import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { reactive } from "@odoo/owl";
import { rotate } from "@web/core/utils/arrays";
import { SuggestionList } from "./suggestion_list";
// import { omit, pick } from "@web/core/utils/objects";

export class SuggestionPlugin extends Plugin {
    static id = "suggestion";
    static dependencies = ["overlay", "selection", "history", "userCommand"];
    static shared = [
        "getSuggestionHandlers",
        "close",
        "open",
        "update",
    ];
    // resources = {
    //     supported_delimiters: ["@"],
    //     suggestion_handlers: [{ id, search, fetch, select }],
    // };
    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.dependencies.overlay.createOverlay(SuggestionList);

        this.state = reactive({});
        this.overlayProps = {
            document: this.document,
            close: () => this.overlay.close(),
            state: this.state,
            activateSuggestion: (currentIndex) => {
                this.state.currentIndex = currentIndex;
            },
            applySuggestion: this.applySuggestion.bind(this),
        };
        this.addDomListener(this.editable.ownerDocument, "keydown", this.onKeyDown);
    }

    /**
     * @param {Object} params
     * @param {PowerboxCommand[]} params.suggestions
     * @param {PowerboxCategory[]} [params.categories]
     * @param {Function} [params.onApplySuggestion=() => {}]
     * @param {Function} [params.onClose=() => {}]
     */
    open({
        suggestions,
        categories,
        onApplySuggestion = () => {},
        onClose = () => {},
    } = {}) {
        this.close();
        this.onApplySuggestion = onApplySuggestion;
        this.onClose = onClose;
        this.update(suggestions, categories);
    }

    /**
     * @param {PowerboxCommand[]} suggestions
     * @param {PowerboxCategory[]} [categories]
     */
    update(suggestions, categories) {
        if (categories) {
            const orderCommands = [];
            for (const category of categories) {
                orderCommands.push(
                    ...suggestions.filter((suggestion) => suggestion.categoryId === category.id)
                );
            }
            suggestions = orderCommands;
        }
        Object.assign(this.state, {
            showCategories: !!categories,
            suggestions,
            currentIndex: 0,
        });
        this.overlay.open({ props: this.overlayProps });
    }

    close() {
        if (!this.overlay.isOpen) {
            return;
        }
        this.onClose();
        this.overlay.close();
    }

    onKeyDown(ev) {
        if (!this.overlay.isOpen) {
            return;
        }
        const key = ev.key;
        switch (key) {
            case "Escape":
                this.close();
                break;
            case "Enter":
            case "Tab":
                ev.preventDefault();
                ev.stopImmediatePropagation();
                this.applySuggestion(this.state.suggestions[this.state.currentIndex]);
                break;
            case "ArrowUp": {
                ev.preventDefault();
                this.state.currentIndex = rotate(
                    this.state.currentIndex,
                    this.state.suggestions,
                    -1
                );
                break;
            }
            case "ArrowDown": {
                ev.preventDefault();
                this.state.currentIndex = rotate(
                    this.state.currentIndex,
                    this.state.suggestions,
                    1
                );
                break;
            }
            case "ArrowLeft":
            case "ArrowRight": {
                this.close();
                break;
            }
        }
    }

    applySuggestion(suggestion) {
        this.onApplySuggestion(suggestion);
        this.close();
    }

    /**
     * @returns {PowerboxCommand[]}
     */
    getSuggestionHandlers() {
        const suggestionHandlers = this.getResource("suggestion_handlers");
        const categoryDict = Object.fromEntries(
            suggestionHandlers.map((handle) => [
                handle.id,
                handle.search,
                handle.fetch,
                handle.select,
            ])
        );
        return categoryDict;
    }

    fetch() {

    }

    search() {

    }

    sort() {

    }

}
