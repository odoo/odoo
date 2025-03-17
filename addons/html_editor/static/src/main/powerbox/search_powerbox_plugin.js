import { fuzzyLookup } from "@web/core/utils/search";
import { Plugin } from "../../plugin";

/**
 * @typedef {import("./powerbox_plugin").PowerboxCategory} CommandGroup
 * @typedef {import("../core/selection_plugin").EditorSelection} EditorSelection
 */

export class SearchPowerboxPlugin extends Plugin {
    static id = "searchPowerbox";
    static dependencies = ["powerbox", "selection", "history", "input"];
    resources = {
        beforeinput_handlers: this.onBeforeInput.bind(this),
        input_handlers: this.onInput.bind(this),
        delete_handlers: this.update.bind(this),
        post_undo_handlers: this.update.bind(this),
        post_redo_handlers: this.update.bind(this),
    };
    setup() {
        const categoryIds = new Set();
        for (const category of this.getResource("powerbox_categories")) {
            if (categoryIds.has(category.id)) {
                throw new Error(`Duplicate category id: ${category.id}`);
            }
            categoryIds.add(category.id);
        }
        this.categories = this.getResource("powerbox_categories");
        this.shouldUpdate = false;
    }
    onBeforeInput(ev) {
        if (ev.data === "/") {
            this.historySavePointRestore = this.dependencies.history.makeSavePoint();
        }
    }
    onInput(ev) {
        if (ev.data === "/") {
            this.openPowerbox();
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
            this.dependencies.powerbox.closePowerbox();
            return;
        }
        const searchTerm = this.searchNode.nodeValue.slice(this.offset + 1, selection.endOffset);
        if (!searchTerm) {
            this.dependencies.powerbox.updatePowerbox(this.enabledCommands, this.categories);
            return;
        }
        if (searchTerm.includes(" ")) {
            this.dependencies.powerbox.closePowerbox();
            return;
        }
        const commands = this.filterCommands(searchTerm);
        if (!commands.length) {
            this.dependencies.powerbox.closePowerbox();
            this.shouldUpdate = true;
            return;
        }
        this.dependencies.powerbox.updatePowerbox(commands);
    }
    /**
     * @param {string} searchTerm
     */
    filterCommands(searchTerm) {
        return fuzzyLookup(searchTerm, this.enabledCommands, (cmd) => [
            cmd.title,
            cmd.categoryName,
            cmd.description,
            ...(cmd.keywords || []),
        ]);
    }
    /**
     * @param {EditorSelection} selection
     */
    isSearching(selection) {
        return (
            selection.endContainer === this.searchNode &&
            this.searchNode.nodeValue &&
            this.searchNode.nodeValue[this.offset] === "/" &&
            selection.endOffset >= this.offset
        );
    }
    openPowerbox() {
        const selection = this.dependencies.selection.getEditableSelection();
        this.offset = selection.startOffset - 1;
        this.enabledCommands = this.dependencies.powerbox.getAvailablePowerboxCommands();
        this.dependencies.powerbox.openPowerbox({
            commands: this.enabledCommands,
            categories: this.categories,
            onApplyCommand: this.historySavePointRestore,
            onClose: () => {
                this.shouldUpdate = false;
            },
        });
        this.shouldUpdate = true;
    }
}
