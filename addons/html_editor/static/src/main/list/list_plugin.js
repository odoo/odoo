import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { wrapInlinesInBlocks, removeClass, setTagName, toggleClass } from "@html_editor/utils/dom";
import {
    getDeepestPosition,
    isEmptyBlock,
    isProtected,
    isVisible,
} from "@html_editor/utils/dom_info";
import { closestElement, descendants, getAdjacents } from "@html_editor/utils/dom_traversal";
import { childNodeIndex } from "@html_editor/utils/position";
import { _t } from "@web/core/l10n/translation";
import {
    applyToTree,
    compareListTypes,
    createList,
    getListMode,
    insertListAfter,
    isListItem,
} from "./utils";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

function isListActive(listMode) {
    return (selection) => {
        const block = closestBlock(selection.anchorNode);
        return block?.tagName === "LI" && getListMode(block.parentNode) === listMode;
    };
}

export class ListPlugin extends Plugin {
    static name = "list";
    static dependencies = ["tabulation", "split", "selection", "delete", "dom"];
    /** @type { (p: ListPlugin) => Record<string, any> } */
    static resources = (p) => ({
        handle_delete_backward: { callback: p.handleDeleteBackward.bind(p) },
        handle_delete_range: { callback: p.handleDeleteRange.bind(p) },
        handle_tab: { callback: p.handleTab.bind(p), sequence: 10 },
        handle_shift_tab: { callback: p.handleShiftTab.bind(p), sequence: 10 },
        split_element_block: { callback: p.handleSplitBlock.bind(p) },
        toolbarGroup: {
            id: "list",
            sequence: 30,
            buttons: [
                {
                    id: "bulleted_list",
                    action(dispatch) {
                        dispatch("TOGGLE_LIST", { mode: "UL" });
                    },
                    icon: "fa-list-ul",
                    name: "Bulleted list",
                    isFormatApplied: isListActive("UL"),
                },
                {
                    id: "numbered_list",
                    action(dispatch) {
                        dispatch("TOGGLE_LIST", { mode: "OL" });
                    },
                    icon: "fa-list-ol",
                    name: "Numbered list",
                    isFormatApplied: isListActive("OL"),
                },
                {
                    id: "checklist",
                    action(dispatch) {
                        dispatch("TOGGLE_LIST", { mode: "CL" });
                    },
                    icon: "fa-check-square-o",
                    name: "Checklist",
                    isFormatApplied: isListActive("CL"),
                },
            ],
        },
        powerboxCommands: [
            {
                name: _t("Bulleted list"),
                description: _t("Create a simple bulleted list"),
                category: "structure",
                fontawesome: "fa-list-ul",
                action(dispatch) {
                    dispatch("TOGGLE_LIST", { mode: "UL" });
                },
            },
            {
                name: _t("Numbered list"),
                description: _t("Create a list with numbering"),
                category: "structure",
                fontawesome: "fa-list-ol",
                action(dispatch) {
                    dispatch("TOGGLE_LIST", { mode: "OL" });
                },
            },
            {
                name: _t("Checklist"),
                description: _t("Track tasks with a checklist"),
                category: "structure",

                fontawesome: "fa-check-square-o",
                action(dispatch) {
                    dispatch("TOGGLE_LIST", { mode: "CL" });
                },
            },
        ],
        emptyBlockHints: [
            { selector: "UL LI", hint: _t("List") },
            { selector: "OL LI", hint: _t("List") },
            // @todo @phoenix: hint for checklists was supposed to be "To-do",
            // but never worked because of the ::before pseudo-element is used
            // to display the checkbox.
        ],
    });

    setup() {
        this.addDomListener(this.editable, "touchstart", this.onPointerdown);
        this.addDomListener(this.editable, "mousedown", this.onPointerdown);
    }

    handleCommand(command, payload) {
        switch (command) {
            case "TOGGLE_LIST":
                this.toggleList(payload.mode);
                break;
            case "NORMALIZE": {
                this.normalize(payload.node);
                break;
            }
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
     * @throws {Error} If an invalid list type is provided.
     */
    toggleList(mode) {
        if (!["UL", "OL", "CL"].includes(mode)) {
            throw new Error(`Invalid list type: ${mode}`);
        }

        // @todo @phoenix: original implementation removed whitespace-only text nodes from traversedNodes.
        // Check if this is necessary.

        const traversedBlocks = this.shared.getTraversedBlocks();

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
                if (getListMode(li.parentElement) === mode) {
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
                this.switchListMode(list, mode);
            }
            for (const block of nonListBlocks) {
                this.blockToList(block, mode);
            }
        } else {
            for (const li of sameModeListItems) {
                this.liToBlocks(li);
            }
        }

        this.dispatch("ADD_STEP");
    }

    normalize(root = this.editable) {
        const closestNestedLI = closestElement(root, "li.oe-nested");
        if (closestNestedLI) {
            root = closestNestedLI.parentElement;
        }
        applyToTree(root, (element) => {
            if (isProtected(element)) {
                return element;
            }
            element = this.liWithoutParentToP(element);
            element = this.mergeSimilarLists(element);
            element = this.normalizeLI(element);
            return element;
        });
    }

    // --------------------------------------------------------------------------
    // Helpers for toggleList
    // --------------------------------------------------------------------------

    /**
     * Switches the list mode of the given list element.
     *
     * @param {HTMLOListElement|HTMLUListElement} list - The list element to switch the mode of.
     * @param {"UL"|"OL"|"CL"} newMode - The new mode to switch to.
     * @returns {HTMLOListElement|HTMLUListElement} The modified list element.
     */
    switchListMode(list, newMode) {
        if (getListMode(list) === newMode) {
            return;
        }
        const newTag = newMode === "CL" ? "UL" : newMode;
        const cursors = this.shared.preserveSelection();
        const newList = setTagName(list, newTag);
        // Clear list style (@todo @phoenix - why??)
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
        cursors.remapNode(list, newList).restore();
        return newList;
    }

    /**
     * @param {HTMLElement} block element
     * @param {"UL"|"OL"|"CL"} mode
     */
    blockToList(element, mode) {
        if (element.tagName === "P") {
            return this.pToList(element, mode);
        }
        // @todo @phoenix: check for callbacks registered as resources instead?
        if (element.matches("td, th, li.nav-item")) {
            return this.blockContentsToList(element, mode);
        }
        let list;
        const cursors = this.shared.preserveSelection();
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
     * @param {HTMLParagraphElement} p
     * @param {"UL"|"OL"|"CL"} mode
     */
    pToList(p, mode) {
        const cursors = this.shared.preserveSelection();
        const list = insertListAfter(this.document, p, mode, [[...p.childNodes]]);
        this.shared.copyAttributes(p, list);
        p.remove();
        cursors.remapNode(p, list.firstChild).restore();
        return list;
    }

    blockContentsToList(block, mode) {
        const cursors = this.shared.preserveSelection();
        const list = insertListAfter(this.document, block.lastChild, mode, [[...block.childNodes]]);
        cursors.remapNode(block, list.firstChild).restore();
        return list;
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
            return element;
        }
        // Transform <li> into <p> if they are not in a <ul> / <ol>.
        const paragraph = document.createElement("p");
        element.replaceWith(paragraph);
        paragraph.replaceChildren(...element.childNodes);
        return paragraph;
    }

    mergeSimilarLists(element) {
        if (!element.matches("ul, ol, li.oe-nested")) {
            return element;
        }
        const previousSibling = element.previousElementSibling;
        if (
            previousSibling &&
            element.isContentEditable &&
            previousSibling.isContentEditable &&
            compareListTypes(previousSibling, element)
        ) {
            const cursors = this.shared.preserveSelection();

            cursors.shiftOffset(element, previousSibling.childNodes.length);
            element.prepend(...previousSibling.childNodes);

            cursors.remapNode(previousSibling, element);
            // @todo @phoenix: what if unremovable/unmergeable?
            previousSibling.remove();

            cursors.restore();
        }
        return element;
    }

    /**
     * Wraps inlines in P to avoid inlines with block siblings.
     */
    normalizeLI(element) {
        if (!isListItem(element) || element.classList.contains("oe-nested")) {
            return element;
        }

        if ([...element.children].some(isBlock)) {
            const cursors = this.shared.preserveSelection();
            wrapInlinesInBlocks(element, cursors);
            cursors.restore();
        }

        return element;
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

        const ul = createList(this.document, getListMode(destul));
        lip.append(ul);

        const cursors = this.shared.preserveSelection();
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
        const cursors = this.shared.preserveSelection();
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
        const cursors = this.shared.preserveSelection();
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

    outdentTopLevelLI(li) {
        const cursors = this.shared.preserveSelection();
        const ul = li.parentNode;
        const dir = ul.getAttribute("dir");
        let p;
        let toMove = li.lastChild;
        while (toMove) {
            if (isBlock(toMove)) {
                if (p && isVisible(p)) {
                    cursors.update(callbacksForCursorUpdate.after(ul, p));
                    ul.after(p);
                }
                p = undefined;
                cursors.update(callbacksForCursorUpdate.after(ul, toMove));
                ul.after(toMove);
            } else {
                p = p || this.document.createElement("P");
                if (dir) {
                    p.setAttribute("dir", dir);
                    p.style.setProperty("text-align", ul.style.getPropertyValue("text-align"));
                }
                cursors.update(callbacksForCursorUpdate.prepend(p, toMove));
                p.prepend(toMove);
            }
            toMove = li.lastChild;
        }
        if (p && isVisible(p)) {
            cursors.update(callbacksForCursorUpdate.after(ul, p));
            ul.after(p);
        }
        cursors.update(callbacksForCursorUpdate.remove(li));
        li.remove();
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
        for (const block of this.shared.getTraversedBlocks()) {
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

    handleTab() {
        const { listItems, navListItems, nonListItems } = this.separateListItems();
        if (listItems.length || navListItems.length) {
            this.indentListNodes(listItems);
            this.shared.indentBlocks(nonListItems);
            // Do nothing to nav-items.
            this.dispatch("ADD_STEP");
            return true;
        }
    }

    handleShiftTab() {
        const { listItems, navListItems, nonListItems } = this.separateListItems();
        if (listItems.length || navListItems.length) {
            this.outdentListNodes(listItems);
            this.shared.outdentBlocks(nonListItems);
            // Do nothing to nav-items.
            this.dispatch("ADD_STEP");
            return true;
        }
    }

    handleSplitBlock(params) {
        const closestLI = closestElement(params.targetNode, "LI");
        if (!closestLI) {
            return;
        }
        if (!closestLI.textContent) {
            this.outdentLI(closestLI);
            return true;
        }
        const [, newLI] = this.shared.splitElementBlock({ ...params, blockToSplit: closestLI });
        if (closestLI.classList.contains("o_checked")) {
            removeClass(newLI, "o_checked");
        }
        const [anchorNode, anchorOffset] = getDeepestPosition(newLI, 0);
        this.shared.setSelection({ anchorNode, anchorOffset });
        return true;
    }

    handleDeleteBackward(range) {
        const { startContainer, startOffset, endContainer, endOffset } = range;
        const closestLIendContainer = closestElement(endContainer, "LI");
        if (!closestLIendContainer) {
            return;
        }
        // Detect if cursor is at beginning of LI (or the editable === collapsed range).
        if (
            (startContainer === endContainer && startOffset === endOffset) ||
            closestElement(startContainer, "LI") !== closestLIendContainer
        ) {
            this.liToBlocks(closestLIendContainer);
            return true;
        }
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

        range = this.shared.deleteRange(range);
        this.shared.setSelection({
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
        const isChecklistItem = node.tagName == "LI" && getListMode(node.parentElement) == "CL";
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
            this.dispatch("ADD_STEP");
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
