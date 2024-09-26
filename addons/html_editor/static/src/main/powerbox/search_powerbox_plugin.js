import { fuzzyLookup } from "@web/core/utils/search";
import { Plugin } from "../../plugin";

/**
 * @typedef {import("./powerbox_plugin").CommandGroup} CommandGroup
 * @typedef {import("../core/selection_plugin").EditorSelection} EditorSelection
 */

export class SearchPowerboxPlugin extends Plugin {
    static name = "search_powerbox";
    static dependencies = ["powerbox", "selection", "history"];
    /** @type { (p: SearchPowerboxPlugin) => Record<string, any> } */
    static resources = (p) => ({
        onBeforeInput: { handler: p.onBeforeInput.bind(p) },
        onInput: { handler: p.onInput.bind(p) },
    });
    setup() {
        const categoryIds = new Set();
        for (const category of this.resources.powerboxCategory) {
            if (categoryIds.has(category.id)) {
                throw new Error(`Duplicate category id: ${category.id}`);
            }
            categoryIds.add(category.id);
        }
        this.categories = this.resources.powerboxCategory.sort((a, b) => a.sequence - b.sequence);
        this.commands = this.resources.powerboxItems.map((command) => ({
            ...command,
            categoryName: this.categories.find((category) => category.id === command.category).name,
        }));

        this.shouldUpdate = false;
    }
    handleCommand(command) {
        switch (command) {
            case "DELETE_BACKWARD":
            case "DELETE_FORWARD":
            case "HISTORY_UNDO":
            case "HISTORY_REDO":
                this.update();
                break;
        }
    }
    onBeforeInput(ev) {
        if (ev.data === "/") {
            this.historySavePointRestore = this.shared.makeSavePoint();
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
        const selection = this.shared.getEditableSelection();
        this.searchNode = selection.startContainer;
        if (!this.isSearching(selection)) {
            this.shared.closePowerbox();
            return;
        }
        const searchTerm = this.searchNode.nodeValue.slice(this.offset + 1, selection.endOffset);
        if (!searchTerm) {
            this.shared.updatePowerbox(this.enabledCommands, this.categories);
            return;
        }
        if (searchTerm.includes(" ")) {
            this.shared.closePowerbox();
            return;
        }
        const commands = this.filterCommands(searchTerm);
        if (!commands.length) {
            this.shared.closePowerbox();
            this.shouldUpdate = true;
            return;
        }
        this.shared.updatePowerbox(commands);
    }
    /**
     * @param {string} searchTerm
     */
    filterCommands(searchTerm) {
        return fuzzyLookup(searchTerm, this.enabledCommands, (cmd) => [
            cmd.name,
            cmd.categoryName,
            cmd.description,
            ...(cmd.searchKeywords || []),
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
        const selection = this.shared.getEditableSelection();
        this.offset = selection.startOffset - 1;
        this.enabledCommands = this.commands.filter(
            (cmd) => !cmd.isAvailable?.(selection.anchorNode)
        );
        this.shared.openPowerbox({
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
