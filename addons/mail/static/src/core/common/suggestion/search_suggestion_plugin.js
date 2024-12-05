import { Plugin } from "@html_editor/plugin";
import { renderToElement } from "@web/core/utils/render";
import { rightPos } from "@html_editor/utils/position";

/**
 * @typedef {import("./suggestion_plugin").PowerboxCategory} CommandGroup
 * @typedef {import("../core/selection_plugin").EditorSelection} EditorSelection
 */

export class SearchSuggestionPlugin extends Plugin {
    static id = "searchSuggestion";
    static dependencies = ["suggestion", "selection", "dom", "history"];
    resources = {
        beforeinput_handlers: this.onBeforeInput.bind(this),
        input_handlers: this.onInput.bind(this),
        delete_handlers: this.update.bind(this),
        post_undo_handlers: this.update.bind(this),
        post_redo_handlers: this.update.bind(this),
    };
    setup() {
        // const categoryIds = new Set();
        // for (const category of this.getResource("powerbox_categories")) {
        //     if (categoryIds.has(category.id)) {
        //         throw new Error(`Duplicate category id: ${category.id}`);
        //     }
        //     categoryIds.add(category.id);
        // }
        this.supportedDelimiters = this.getResource("supported_delimiters");
        this.shouldUpdate = false;
    }
    onBeforeInput(ev) {
        if (ev.data === "@") {
            this.historySavePointRestore = this.dependencies.history.makeSavePoint();
        }
    }
    onInput(ev) {
        if (ev.data === "@") {
            this.open();
        } else {
            this.update();
        }
    }
    update() {
        if (!this.shouldUpdate) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        this.searchNode = selection.startContainer;
        if (!this.isSearching(selection)) {
            this.dependencies.suggestion.close();
            return;
        }
        const searchTerm = this.searchNode.nodeValue.slice(this.offset + 1, selection.endOffset);
        if (!searchTerm) {
            // this.dependencies.suggestion.update(
            //     this.enabledCommands,
            //     this.categories
            // );
            return;
        }
        if (searchTerm.includes(" ")) {
            this.dependencies.suggestion.close();
            return;
        }
        const commands = this.filterCommands(searchTerm);
        if (!commands.length) {
            this.dependencies.suggestion.close();
            this.shouldUpdate = true;
            return;
        }
        this.dependencies.suggestion.update(commands);
    }
    /**
     * @param {string} searchTerm
     */
    filterCommands(searchTerm) {
        return [{ title: "Marc Demo", categoryName: "parter", description: "mark@example.com" }];
    }
    /**
     * @param {EditorSelection} selection
     */
    isSearching(selection) {
        return (
            selection.endContainer === this.searchNode &&
            this.searchNode.nodeValue &&
            this.searchNode.nodeValue[this.offset] === "@" &&
            selection.endOffset >= this.offset
        );
    }
    open() {
        const selection = this.dependencies.selection.getEditableSelection();
        this.offset = selection.startOffset - 1;
        this.enabledCommands = [{ title: "test", categoryName: "test", description: "test" }];
        this.dependencies.suggestion.open({
            suggestions: this.enabledCommands,
            categories: this.categories,
            onApplySuggestion: () => {
                this.historySavePointRestore();
                const partnerBlock = renderToElement("mail.Suggestion.Partner", {
                    href: `wow`,
                    partnerId: 1,
                    displayName: "Marc Demo",
                });
                this.dependencies.dom.insert(partnerBlock);
                const [anchorNode, anchorOffset] = rightPos(partnerBlock);
                this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
                this.dependencies.history.addStep();
            },
            onClose: () => {
                this.shouldUpdate = false;
            },
        });
        this.shouldUpdate = true;
    }
}
