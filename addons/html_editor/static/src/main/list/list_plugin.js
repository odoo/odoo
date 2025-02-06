import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { removeClass, toggleClass, wrapInlinesInBlocks } from "@html_editor/utils/dom";
import {
    getDeepestPosition,
    isEmptyBlock,
    isListElement,
    isListItemElement,
    isParagraphRelatedElement,
    isProtected,
    isProtecting,
    listElementSelector,
} from "@html_editor/utils/dom_info";
import {
    closestElement,
    descendants,
    getAdjacents,
    selectElements,
    ancestors,
    childNodes,
} from "@html_editor/utils/dom_traversal";
import { childNodeIndex } from "@html_editor/utils/position";
import { leftLeafOnlyNotBlockPath } from "@html_editor/utils/dom_state";
import { _t } from "@web/core/l10n/translation";
import { compareListTypes, createList, insertListAfter, isListItem } from "./utils";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { withSequence } from "@html_editor/utils/resource";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";

export class ListPlugin extends Plugin {
    static id = "list";
    static dependencies = [
        "baseContainer",
        "tabulation",
        "history",
        "input",
        "split",
        "selection",
        "delete",
        "dom",
    ];
    resources = {
        user_commands: [
            {
                id: "toggleList",
                run: this.toggleListCommand.bind(this),
            },
            {
                id: "toggleListUL",
                title: _t("Bulleted list"),
                description: _t("Create a simple bulleted list"),
                icon: "fa-list-ul",
                run: () => this.toggleListCommand({ mode: "UL" }),
            },
            {
                id: "toggleListOL",
                title: _t("Numbered list"),
                description: _t("Create a list with numbering"),
                icon: "fa-list-ol",
                run: () => this.toggleListCommand({ mode: "OL" }),
            },
            {
                id: "toggleListCL",
                title: _t("Checklist"),
                description: _t("Track tasks with a checklist"),
                icon: "fa-check-square-o",
                run: () => this.toggleListCommand({ mode: "CL" }),
            },
        ],
        toolbar_groups: withSequence(30, { id: "list" }),
        toolbar_items: [
            {
                id: "bulleted_list",
                groupId: "list",
                commandId: "toggleListUL",
                isActive: this.isListActive("UL"),
            },
            {
                id: "numbered_list",
                groupId: "list",
                commandId: "toggleListOL",
                isActive: this.isListActive("OL"),
            },
            {
                id: "checklist",
                groupId: "list",
                commandId: "toggleListCL",
                isActive: this.isListActive("CL"),
            },
        ],
        powerbox_items: [
            {
                categoryId: "structure",
                commandId: "toggleListUL",
            },
            {
                categoryId: "structure",
                commandId: "toggleListOL",
            },
            {
                categoryId: "structure",
                commandId: "toggleListCL",
            },
        ],
        power_buttons: [
            { commandId: "toggleListUL" },
            { commandId: "toggleListOL" },
            { commandId: "toggleListCL" },
        ],

        hints: [{ selector: "LI", text: _t("List") }],

        /** Handlers */
        input_handlers: this.onInput.bind(this),
        normalize_handlers: this.normalize.bind(this),

        /** Overrides */
        delete_backward_overrides: this.handleDeleteBackward.bind(this),
        delete_range_overrides: this.handleDeleteRange.bind(this),
        tab_overrides: this.handleTab.bind(this),
        shift_tab_overrides: this.handleShiftTab.bind(this),
        split_element_block_overrides: this.handleSplitBlock.bind(this),
        node_to_insert_processors: this.processNodeToInsert.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "touchstart", this.onPointerdown);
        this.addDomListener(this.editable, "mousedown", this.onPointerdown);
    }

    toggleListCommand({ mode } = {}) {
        this.toggleList(mode);
        this.dependencies.history.addStep();
    }

    onInput(ev) {
        if (ev.data !== " ") {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        const blockEl = closestBlock(selection.anchorNode);
        const leftDOMPath = leftLeafOnlyNotBlockPath(selection.anchorNode);
        let spaceOffset = selection.anchorOffset;
        let leftLeaf = leftDOMPath.next().value;
        while (leftLeaf) {
            // Calculate spaceOffset by adding lengths of previous text nodes
            // to correctly find offset position for selection within inline
            // elements. e.g. <p>ab<strong>cd[]e</strong></p>
            spaceOffset += leftLeaf.length;
            leftLeaf = leftDOMPath.next().value;
        }
        const stringToConvert = blockEl.textContent.substring(0, spaceOffset);
        const shouldCreateNumberList = /^(?:[1aA])[.)]\s$/.test(stringToConvert);
        const shouldCreateBulletList = /^[-*]\s$/.test(stringToConvert);
        const shouldCreateCheckList = /^\[\]\s$/.test(stringToConvert);
        if (
            (shouldCreateNumberList || shouldCreateBulletList || shouldCreateCheckList) &&
            !closestElement(selection.anchorNode, "li")
        ) {
            this.dependencies.selection.setSelection({
                anchorNode: blockEl.firstChild,
                anchorOffset: 0,
                focusNode: selection.focusNode,
                focusOffset: selection.focusOffset,
            });
            this.dependencies.delete.deleteSelection();
            if (shouldCreateNumberList) {
                const listStyle = { a: "lower-alpha", A: "upper-alpha", 1: null }[
                    stringToConvert.substring(0, 1)
                ];
                this.toggleList("OL", listStyle);
            } else if (shouldCreateBulletList) {
                this.toggleList("UL");
            } else if (shouldCreateCheckList) {
                this.toggleList("CL");
            }
            this.dependencies.history.addStep();
        }
    }

    // --------------------------------------------------------------------------
    // Commands
    // --------------------------------------------------------------------------

    /**
     * Classifies the selected blocks into three categories:
     * - LI that are part of a list of the same mode as the target one.
     * - Lists (UL or OL) that need to have its mode switched to the target mode.
     * - Blocks that need to be converted to lists.
     *
     *  If (and only if) all blocks fall into the first category, the list items
     *  are converted into paragraphs (result is toggle list OFF).
     *  Otherwise, the LIs in this category remain unchanged and the other two
     *  categories are processed.
     *
     * @param {string} mode - The list mode to toggle (UL, OL, CL).
     * @param {string} [listStyle] - The list style ( see listStyle css property)
     * @throws {Error} If an invalid list type is provided.
     */
    toggleList(mode, listStyle) {
        if (!["UL", "OL", "CL"].includes(mode)) {
            throw new Error(`Invalid list type: ${mode}`);
        }
        if (mode === "CL" && !!listStyle) {
            throw new Error(`listStyle is not compatible with "CL" list type`);
        }

        // @todo @phoenix: original implementation removed whitespace-only text nodes from traversedNodes.
        // Check if this is necessary.

        const traversedBlocks = this.dependencies.selection.getTraversedBlocks();

        // Keep deepest blocks only.
        for (const block of traversedBlocks) {
            if (descendants(block).some((descendant) => traversedBlocks.has(descendant))) {
                traversedBlocks.delete(block);
            }
        }

        // Classify traversed blocks.
        const sameModeListItems = new Set();
        const nonListBlocks = new Set();
        const listsToSwitch = new Set();
        for (const block of traversedBlocks) {
            if (["OL", "UL"].includes(block.tagName) || !block.isContentEditable) {
                continue;
            }
            const li = closestElement(block, isListItem);
            if (li) {
                if (this.getListMode(li.parentElement) === mode) {
                    sameModeListItems.add(li);
                } else {
                    listsToSwitch.add(li.parentElement);
                }
            } else {
                nonListBlocks.add(block);
            }
        }

        // Apply changes.
        if (listsToSwitch.size || nonListBlocks.size) {
            for (const list of listsToSwitch) {
                const cursors = this.dependencies.selection.preserveSelection();
                const newList = this.switchListMode(list, mode);
                cursors.remapNode(list, newList).restore();
            }
            for (const block of nonListBlocks) {
                const list = this.blockToList(block, mode, listStyle);
                if (listStyle) {
                    list.style.listStyle = listStyle;
                }
            }
        } else {
            for (const li of sameModeListItems) {
                this.liToBlocks(li);
            }
        }
    }

    normalize(root = this.editable) {
        const closestNestedLI = closestElement(root, "li.oe-nested");
        if (closestNestedLI) {
            root = closestNestedLI.parentElement;
        }
        for (const element of selectElements(root, "ul, ol, li")) {
            if (isProtected(element) || isProtecting(element)) {
                continue;
            }
            for (const fn of [
                this.liWithoutParentToP,
                this.mergeSimilarLists,
                this.normalizeLI,
                this.normalizeNestedList,
            ]) {
                fn.call(this, element);
            }
        }
    }

    // --------------------------------------------------------------------------
    // Helpers for toggleList
    // --------------------------------------------------------------------------

    /**
     * @param {HTMLElement} element
     * @param {"UL"|"OL"|"CL"} mode
     */
    blockToList(element, mode) {
        if (element.matches(baseContainerGlobalSelector)) {
            return this.baseContainerToList(element, mode);
        }
        // @todo @phoenix: check for callbacks registered as resources instead?
        if (element.matches("td, th, li.nav-item")) {
            return this.blockContentsToList(element, mode);
        }
        let list;
        const cursors = this.dependencies.selection.preserveSelection();
        if (element === this.editable) {
            // @todo @phoenix: check if this is needed
            // Refactor insertListAfter in order to make proper preserveCursor
            // possible.
            const callingNode = element.firstChild;
            const group = getAdjacents(callingNode, (n) => !isBlock(n));
            list = insertListAfter(this.document, callingNode, mode, [group]);
        } else {
            const parent = element.parentNode;
            const childIndex = childNodeIndex(element);
            list = insertListAfter(this.document, element, mode, [element]);
            cursors.update((cursor) => {
                if (cursor.node === parent) {
                    if (cursor.offset === childIndex) {
                        [cursor.node, cursor.offset] = [list.firstChild, 0];
                    } else if (cursor.offset === childIndex + 1) {
                        [cursor.node, cursor.offset] = [list.firstChild, 1];
                    }
                }
            });
            if (element.hasAttribute("dir")) {
                list.setAttribute("dir", element.getAttribute("dir"));
            }
        }
        cursors.restore();
        return list;
    }

    /**
     * @param {HTMLElement} baseContainer baseContainer Element (can be a div with the
     *        necessary classes/attributes).
     * @param {"UL"|"OL"|"CL"} mode
     */
    baseContainerToList(baseContainer, mode) {
        const cursors = this.dependencies.selection.preserveSelection();
        const list = insertListAfter(this.document, baseContainer, mode, [
            childNodes(baseContainer),
        ]);
        this.dependencies.dom.copyAttributes(baseContainer, list);
        baseContainer.remove();
        cursors.remapNode(baseContainer, list.firstChild).restore();
        return list;
    }

    blockContentsToList(block, mode) {
        const cursors = this.dependencies.selection.preserveSelection();
        const list = insertListAfter(this.document, block.lastChild, mode, [[...block.childNodes]]);
        cursors.remapNode(block, list.firstChild).restore();
        return list;
    }

    /**
     * Converts a list element and its nested elements to the given list mode.
     *
     * @see switchListMode
     * @param {HTMLUListElement|HTMLOListElement|HTMLLIElement} node - HTML element
     * representing a list or list item.
     * @param {string} newMode - Target list mode
     * @param {Object} options
     * @returns {HTMLUListElement|HTMLOListElement|HTMLLIElement} node - Modified
     * list element after conversion.
     */
    convertList(node, newMode) {
        if (!["UL", "OL", "LI"].includes(node.tagName)) {
            return;
        }
        const listMode = this.getListMode(node);
        if (listMode && newMode !== listMode) {
            node = this.switchListMode(node, newMode);
        }
        for (const child of node.children) {
            this.convertList(child, newMode);
        }
        return node;
    }

    getListMode(listContainerEl) {
        if (!["UL", "OL"].includes(listContainerEl.tagName)) {
            return;
        }
        if (listContainerEl.tagName === "OL") {
            return "OL";
        }
        return listContainerEl.classList.contains("o_checklist") ? "CL" : "UL";
    }

    isListActive(listMode) {
        return (selection) => {
            const block = closestBlock(selection.anchorNode);
            return block?.tagName === "LI" && this.getListMode(block.parentNode) === listMode;
        };
    }

    /**
     * Switches the list mode of the given list element.
     *
     * @param {HTMLOListElement|HTMLUListElement} list - The list element to switch the mode of.
     * @param {"UL"|"OL"|"CL"} newMode - The new mode to switch to.
     * @param {Object} options
     * @returns {HTMLOListElement|HTMLUListElement} The modified list element.
     */
    switchListMode(list, newMode) {
        if (this.getListMode(list) === newMode) {
            return;
        }
        const newTag = newMode === "CL" ? "UL" : newMode;
        const newList = this.dependencies.dom.setTagName(list, newTag);
        // Clear list style (@todo @phoenix - why??)
        newList.style.removeProperty("list-style");
        for (const li of newList.children) {
            if (li.style.listStyle !== "none") {
                li.style.listStyle = null;
                if (!li.style.all) {
                    li.removeAttribute("style");
                }
            }
        }
        removeClass(newList, "o_checklist");
        if (newMode === "CL") {
            newList.classList.add("o_checklist");
        }
        return newList;
    }

    /**
     * Unwraps LI's content into blocks. Equivalent to fully outdenting the LI.
     *
     * @param {HTMLLIElement} li
     */
    liToBlocks(li) {
        while (li) {
            li = this.outdentLI(li);
        }
    }

    // --------------------------------------------------------------------------
    // Helpers for normalize
    // --------------------------------------------------------------------------

    liWithoutParentToP(element) {
        const isOrphan = element.nodeName === "LI" && !element.closest("ul, ol");
        if (!isOrphan) {
            return;
        }
        // Transform <li> into <p> if they are not in a <ul> / <ol>.
        const paragraph = this.dependencies.baseContainer.createBaseContainer();
        element.replaceWith(paragraph);
        paragraph.replaceChildren(...element.childNodes);
    }

    mergeSimilarLists(element) {
        if (!element.matches("ul, ol, li.oe-nested")) {
            return;
        }
        const previousSibling = element.previousElementSibling;
        if (
            previousSibling &&
            element.isContentEditable &&
            previousSibling.isContentEditable &&
            compareListTypes(previousSibling, element)
        ) {
            const cursors = this.dependencies.selection.preserveSelection();
            cursors.update(callbacksForCursorUpdate.merge(element));
            previousSibling.append(...element.childNodes);
            // @todo @phoenix: what if unremovable/unmergeable?
            element.remove();

            cursors.restore();
        }
    }

    /**
     * Wraps inlines in P to avoid inlines with block siblings.
     */
    normalizeLI(element) {
        if (!isListItem(element) || element.classList.contains("oe-nested")) {
            return;
        }

        if (
            [...element.children].some(
                (child) => isBlock(child) && !this.dependencies.split.isUnsplittable(child)
            )
        ) {
            const cursors = this.dependencies.selection.preserveSelection();
            wrapInlinesInBlocks(element, {
                baseContainerNodeName: this.dependencies.baseContainer.getDefaultNodeName(),
                cursors,
            });
            cursors.restore();
        }
    }

    normalizeNestedList(element) {
        if (element.tagName === "LI") {
            return;
        }
        if (["UL", "OL"].includes(element.parentElement?.tagName)) {
            const cursors = this.dependencies.selection.preserveSelection();
            const li = this.document.createElement("li");
            element.parentElement.insertBefore(li, element);
            li.appendChild(element);
            li.classList.add("oe-nested");
            cursors.restore();
        }
    }

    // --------------------------------------------------------------------------
    // Indentation
    // --------------------------------------------------------------------------

    // @temp comment: former oTab
    /**
     * @param {HTMLLIElement} li
     */
    indentLI(li) {
        const lip = this.document.createElement("li");
        lip.classList.add("oe-nested");
        const destul =
            li.previousElementSibling?.querySelector("ol, ul") ||
            li.nextElementSibling?.querySelector("ol, ul") ||
            li.closest("ol, ul");

        const ul = createList(this.document, this.getListMode(destul));
        lip.append(ul);

        const cursors = this.dependencies.selection.preserveSelection();
        // lip replaces li
        li.before(lip);
        ul.append(li);
        cursors.update((cursor) => {
            if (cursor.node === lip.parentNode) {
                const childIndex = childNodeIndex(lip);
                if (cursor.offset === childIndex) {
                    [cursor.node, cursor.offset] = [ul, 0];
                } else if (cursor.offset === childIndex + 1) {
                    [cursor.node, cursor.offset] = [ul, 1];
                }
            }
        });
        cursors.restore();
    }

    // @temp comment: former oShiftTab
    /**
     * @param {HTMLLIElement} li
     * @returns {HTMLLIElement|null} li or null if it no longer exists.
     */
    outdentLI(li) {
        if (li.nextElementSibling) {
            this.splitList(li.nextElementSibling);
        }

        if (isListItem(li.parentNode.parentNode)) {
            this.outdentNestedLI(li);
            return li;
        }
        this.outdentTopLevelLI(li);
        return null;
    }

    /**
     * Splits a list at the given LI element (li is moved to the new list).
     *
     * @param {HTMLLIElement} li
     */
    splitList(li) {
        const cursors = this.dependencies.selection.preserveSelection();
        // Create new list
        const currentList = li.parentElement;
        const newList = currentList.cloneNode(false);
        if (isListItem(li.parentNode.parentNode)) {
            // li is nested list item
            const lip = this.document.createElement("li");
            lip.classList.add("oe-nested");
            lip.append(newList);
            cursors.update(callbacksForCursorUpdate.after(li.parentNode.parentNode, lip));
            li.parentNode.parentNode.after(lip);
        } else {
            cursors.update(callbacksForCursorUpdate.after(li.parentNode, newList));
            li.parentNode.after(newList);
        }
        // Move nodes to new list
        while (li.nextSibling) {
            cursors.update(callbacksForCursorUpdate.append(newList, li.nextSibling));
            newList.append(li.nextSibling);
        }
        cursors.update(callbacksForCursorUpdate.prepend(newList, li));
        newList.prepend(li);
        cursors.restore();
        return newList;
    }

    outdentNestedLI(li) {
        const cursors = this.dependencies.selection.preserveSelection();
        const ul = li.parentNode;
        const lip = ul.parentNode;
        // Move LI
        cursors.update(callbacksForCursorUpdate.after(lip, li));
        lip.after(li);

        // Remove UL and LI.oe-nested if left empty.
        if (!ul.children.length) {
            cursors.update(callbacksForCursorUpdate.remove(ul));
            ul.remove();
        }
        // @todo @phoenix: not sure in which scenario lip would not have
        // oe-nested class
        if (!lip.children.length && lip.classList.contains("oe-nested")) {
            cursors.update(callbacksForCursorUpdate.remove(lip));
            lip.remove();
        }
        cursors.restore();
    }

    /**
     * @param {HTMLLIElement} li
     */
    outdentTopLevelLI(li) {
        const cursors = this.dependencies.selection.preserveSelection();
        const ul = li.parentNode;
        const dir = ul.getAttribute("dir");
        const textAlign = ul.style.getPropertyValue("text-align");
        wrapInlinesInBlocks(li, {
            baseContainerNodeName: this.dependencies.baseContainer.getDefaultNodeName(),
            cursors,
        });
        if (!li.hasChildNodes()) {
            // Outdenting an empty LI produces an empty baseContainer
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.append(this.document.createElement("br"));
            li.append(baseContainer);
            cursors.remapNode(li, baseContainer);
        }
        // Move LI's children to after UL
        for (const block of childNodes(li).reverse()) {
            if (dir && !block.getAttribute("dir")) {
                block.setAttribute("dir", dir);
            }
            if (textAlign && !block.style.getPropertyValue("text-align")) {
                block.style.setProperty("text-align", textAlign);
            }
            cursors.update(callbacksForCursorUpdate.after(ul, block));
            ul.after(block);
        }
        // Remove LI
        cursors.update(callbacksForCursorUpdate.remove(li));
        li.remove();
        // Remove UL if left empty
        if (!ul.firstElementChild) {
            cursors.update(callbacksForCursorUpdate.remove(ul));
            ul.remove();
        }
        cursors.restore();
    }

    indentListNodes(listNodes) {
        for (const li of listNodes) {
            this.indentLI(li);
        }
    }

    outdentListNodes(listNodes) {
        for (const li of listNodes) {
            this.outdentLI(li);
        }
    }

    separateListItems() {
        const listItems = new Set();
        const navListItems = new Set();
        const nonListItems = [];
        for (const block of this.dependencies.selection.getTraversedBlocks()) {
            const closestLI = block.closest("li");
            if (closestLI) {
                if (closestLI.classList.contains("nav-item")) {
                    navListItems.add(closestLI);
                } else if (!closestLI.querySelector("li") && closestLI.isContentEditable) {
                    // Keep deepest list items only.
                    listItems.add(closestLI);
                }
            } else if (!["UL", "OL"].includes(block.tagName)) {
                nonListItems.push(block);
            }
        }
        return { listItems: [...listItems], navListItems: [...navListItems], nonListItems };
    }

    // --------------------------------------------------------------------------
    // Handlers of other plugins commands
    // --------------------------------------------------------------------------

    processNodeToInsert({ nodeToInsert, container }) {
        if (isListItemElement(container) && isParagraphRelatedElement(nodeToInsert)) {
            nodeToInsert = this.dependencies.dom.setTagName(nodeToInsert, "LI");
        }
        const listEl = container && closestElement(container, listElementSelector);
        if (!listEl) {
            return nodeToInsert;
        }
        const mode = container && this.getListMode(listEl);
        if (
            (isListItemElement(nodeToInsert) && nodeToInsert.classList.contains("oe-nested")) ||
            isListElement(nodeToInsert)
        ) {
            return this.convertList(nodeToInsert, mode);
        }
        return nodeToInsert;
    }

    handleTab() {
        const selection = this.dependencies.selection.getEditableSelection();
        const closestLI = closestElement(selection.anchorNode, "LI");
        if (closestLI) {
            const block = closestBlock(selection.anchorNode);
            const isLiContainsUnSpittable =
                isParagraphRelatedElement(block) &&
                ancestors(block, closestLI).find((node) =>
                    this.dependencies.split.isUnsplittable(node)
                );
            if (isLiContainsUnSpittable) {
                return;
            }
        }
        const { listItems, navListItems, nonListItems } = this.separateListItems();
        if (listItems.length || navListItems.length) {
            this.indentListNodes(listItems);
            this.dependencies.tabulation.indentBlocks(nonListItems);
            // Do nothing to nav-items.
            this.dependencies.history.addStep();
            return true;
        }
    }

    handleShiftTab() {
        const selection = this.dependencies.selection.getEditableSelection();
        const closestLI = closestElement(selection.anchorNode, "LI");
        if (closestLI) {
            const block = closestBlock(selection.anchorNode);
            const isLiContainsUnSpittable =
                isParagraphRelatedElement(block) &&
                ancestors(block, closestLI).find((node) =>
                    this.dependencies.split.isUnsplittable(node)
                );
            if (isLiContainsUnSpittable) {
                return;
            }
        }
        const { listItems, navListItems, nonListItems } = this.separateListItems();
        if (listItems.length || navListItems.length) {
            this.outdentListNodes(listItems);
            this.dependencies.tabulation.outdentBlocks(nonListItems);
            // Do nothing to nav-items.
            this.dependencies.history.addStep();
            return true;
        }
    }

    handleSplitBlock(params) {
        const closestLI = closestElement(params.targetNode, "LI");
        const isBlockUnsplittable =
            closestLI &&
            Array.from(closestLI.childNodes).some(
                (node) => isBlock(node) && this.dependencies.split.isUnsplittable(node)
            );
        if (!closestLI || isBlockUnsplittable) {
            return;
        }
        if (!closestLI.textContent) {
            this.outdentLI(closestLI);
            return true;
        }
        const [, newLI] = this.dependencies.split.splitElementBlock({
            ...params,
            blockToSplit: closestLI,
        });
        if (closestLI.classList.contains("o_checked")) {
            removeClass(newLI, "o_checked");
        }
        const [anchorNode, anchorOffset] = getDeepestPosition(newLI, 0);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        return true;
    }

    /**
     * Fully outdent list item if cursor is at its beginning.
     */
    handleDeleteBackward(range) {
        const { startContainer, startOffset, endContainer, endOffset } = range;
        const closestLIendContainer = closestElement(endContainer, "LI");
        if (!closestLIendContainer) {
            return;
        }
        // Detect if cursor is at beginning of LI (or the editable === collapsed range).
        const isCursorAtStartofLI =
            (startContainer === endContainer && startOffset === endOffset) ||
            closestElement(startContainer, "LI") !== closestLIendContainer;
        if (!isCursorAtStartofLI) {
            return;
        }
        // Check if li or parent list(s) are unsplittable.
        let element = closestLIendContainer;
        while (["LI", "UL", "OL"].includes(element.tagName)) {
            if (this.dependencies.split.isUnsplittable(element)) {
                return;
            }
            element = element.parentElement;
        }
        // Fully outdent LI.
        this.liToBlocks(closestLIendContainer);
        return true;
    }

    // Uncheck checklist item left empty after deleting a multi-LI selection.
    handleDeleteRange(range) {
        const { startContainer, endContainer } = range;
        const startCheckedLi = closestElement(startContainer, "li.o_checked");
        if (!startCheckedLi) {
            return;
        }
        const endLi = closestElement(endContainer, "li");
        if (startCheckedLi === endLi) {
            return;
        }

        range = this.dependencies.delete.deleteRange(range);
        this.dependencies.selection.setSelection({
            anchorNode: range.startContainer,
            anchorOffset: range.startOffset,
        });

        if (isEmptyBlock(startCheckedLi)) {
            removeClass(startCheckedLi, "o_checked");
        }

        return true;
    }

    // --------------------------------------------------------------------------
    // Event handlers
    // --------------------------------------------------------------------------

    /**
     * @param {MouseEvent | TouchEvent} ev
     */
    onPointerdown(ev) {
        const node = ev.target;
        const isChecklistItem =
            node.tagName == "LI" && this.getListMode(node.parentElement) == "CL";
        if (!isChecklistItem) {
            return;
        }
        let offsetX = ev.offsetX;
        let offsetY = ev.offsetY;
        if (ev.type === "touchstart") {
            const rect = node.getBoundingClientRect();
            offsetX = ev.touches[0].clientX - rect.x;
            offsetY = ev.touches[0].clientY - rect.y;
        }

        if (isChecklistItem && this.isPointerInsideCheckbox(node, offsetX, offsetY)) {
            toggleClass(node, "o_checked");
            ev.preventDefault();
            this.dependencies.history.addStep();
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLLIElement} li - LI element inside a checklist.
     */
    isPointerInsideCheckbox(li, pointerOffsetX, pointerOffsetY) {
        const beforeStyle = this.document.defaultView.getComputedStyle(li, ":before");
        const checkboxPosition = {
            left: parseInt(beforeStyle.left),
            top: parseInt(beforeStyle.top),
        };
        checkboxPosition.right = checkboxPosition.left + parseInt(beforeStyle.width);
        checkboxPosition.bottom = checkboxPosition.top + parseInt(beforeStyle.height);

        return (
            pointerOffsetX >= checkboxPosition.left &&
            pointerOffsetX <= checkboxPosition.right &&
            pointerOffsetY >= checkboxPosition.top &&
            pointerOffsetY <= checkboxPosition.bottom
        );
    }
}
