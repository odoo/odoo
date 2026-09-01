/** @odoo-module native */
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { getTextColorOrClass, TEXT_CLASSES_REGEX } from "@html_editor/utils/color";
import {
    removeClass,
    removeEmptyTextNodes,
    removeStyle,
    toggleClass,
    unwrapContents,
    wrapInlinesInBlocks,
} from "@html_editor/utils/dom";
import {
    getDeepestPosition,
    isElement,
    isEmptyBlock,
    isListElement,
    isListItemElement,
    isParagraphRelatedElement,
    isPhrasingContent,
    isProtected,
    isProtecting,
    isShrunkBlock,
    isVisibleTextNode,
    listElementSelector,
} from "@html_editor/utils/dom_info";
import {
    ancestors,
    childNodes,
    closestElement,
    descendants,
    firstLeaf,
    getAdjacents,
    lastLeaf,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import {
    FONT_SIZE_CLASSES,
    getFontSizeOrClass,
    getHtmlStyle,
} from "@html_editor/utils/formatting";
import { weakMemoize } from "@html_editor/utils/functions";
import { childNodeIndex, nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/translation";
import { pick } from "@web/core/utils/collections/objects";
import { isColorGradient } from "@web/core/utils/format/colors";

import { composeToolbarButton } from "../toolbar/toolbar.js";
import { ListSelector } from "./list_selector.js";
import { compareListTypes, createList, insertListAfter, isListItem } from "./utils.js";

const listSelectorItems = [
    {
        id: "bulleted_list",
        commandId: "toggleListUL",
        mode: "UL",
    },
    {
        id: "numbered_list",
        commandId: "toggleListOL",
        mode: "OL",
    },
    {
        id: "checklist",
        commandId: "toggleListCL",
        mode: "CL",
    },
];

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
        "color",
    ];
    static defaultConfig = {
        allowChecklist: true,
    };
    toolbarListSelectorKey = reactive({ value: 0 });
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "toggleListUL",
                title: _t("Bulleted list"),
                description: _t("Create a simple bulleted list"),
                icon: "fa-solid fa-list-ul",
                run: () => this.toggleListCommand({ mode: "UL" }),
                isAvailable: this.canToggleList.bind(this),
            },
            {
                id: "toggleListOL",
                title: _t("Numbered list"),
                description: _t("Create a list with numbering"),
                icon: "fa-solid fa-list-ol",
                run: ({ listStyle } = {}) =>
                    this.toggleListCommand({ mode: "OL", listStyle }),
                isAvailable: this.canToggleList.bind(this),
            },
            {
                id: "toggleListCL",
                title: _t("Checklist"),
                description: _t("Track tasks with a checklist"),
                icon: "fa-regular fa-square-check",
                run: () => this.toggleListCommand({ mode: "CL" }),
                isAvailable: (selection) =>
                    this.config.allowChecklist && this.canToggleList(selection),
            },
        ],
        shortcuts: [
            { hotkey: "control+shift+7", commandId: "toggleListOL" },
            { hotkey: "control+shift+8", commandId: "toggleListUL" },
            { hotkey: "control+shift+9", commandId: "toggleListCL" },
        ],
        shorthands: [
            {
                pattern: /^1[.)]$/,
                commandId: "toggleListOL",
            },
            {
                pattern: /^a[.)]$/,
                commandId: "toggleListOL",
                commandParams: { listStyle: "lower-alpha" },
            },
            {
                pattern: /^A[.)]$/,
                commandId: "toggleListOL",
                commandParams: { listStyle: "upper-alpha" },
            },
            {
                pattern: /^[-*]$/,
                commandId: "toggleListUL",
            },
            {
                pattern: /^\[\]$/,
                commandId: "toggleListCL",
            },
        ],
        toolbar_items: [
            withSequence(5, {
                id: "list",
                groupId: "layout",
                description: _t("Toggle List"),
                Component: ListSelector,
                props: {
                    getButtons: () => this.listSelectorButtons,
                    getListMode: this.getListMode.bind(this),
                    key: this.toolbarListSelectorKey,
                },
                isAvailable: this.canToggleList.bind(this),
            }),
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
        ].map((item) => withSequence(5, item)),
        power_buttons: [
            { commandId: "toggleListUL" },
            { commandId: "toggleListOL" },
            { commandId: "toggleListCL" },
        ].map((item) => withSequence(15, item)),

        hints: [
            { selector: `LI, LI > ${baseContainerGlobalSelector}`, text: _t("List") },
        ],

        normalize_handlers: this.normalize.bind(this),
        step_added_handlers: this.updateToolbarButtons.bind(this),
        delete_handlers: this.adjustListPaddingOnDelete.bind(this),

        delete_backward_overrides: this.handleDeleteBackward.bind(this),
        delete_range_overrides: this.handleDeleteRange.bind(this),
        tab_overrides: this.handleTab.bind(this),
        shift_tab_overrides: this.handleShiftTab.bind(this),
        split_element_block_overrides: this.handleSplitBlock.bind(this),
        color_apply_overrides: this.applyColorToListItem.bind(this),
        format_selection_handlers: this.applyFormatToListItem.bind(this),
        node_to_insert_processors: this.processNodeToInsert.bind(this),
        clipboard_content_processors: this.processContentForClipboard.bind(this),
        before_insert_within_pre_processors: this.insertListWithinPre.bind(this),
        before_insert_processors: this.handleInsert.bind(this),
        triple_click_overrides: this.handleTripleClick.bind(this),

        fully_selected_node_predicates: (node, selection, range) => {
            if (node.nodeName === "LI") {
                const nonListChildren = childNodes(node).filter(
                    (n) => !["UL", "OL"].includes(n.nodeName),
                );
                if (!nonListChildren.length) {
                    return;
                }
                const startLeaf = firstLeaf(nonListChildren[0]);
                const endLeaf = lastLeaf(nonListChildren[nonListChildren.length - 1]);
                return (
                    range.isPointInRange(startLeaf, 0) &&
                    range.isPointInRange(endLeaf, nodeSize(endLeaf))
                );
            }
        },
    };

    setup() {
        this.addDomListener(this.editable, "touchstart", this.onPointerdown);
        this.addDomListener(this.editable, "mousedown", this.onPointerdown);
        this.listSelectorButtons = this.getListSelectorButtons();
        this.canToggleListMemoized = weakMemoize(
            (selection) =>
                isHtmlContentSupported(selection) &&
                this.getBlocksToToggleList().length > 0,
        );
    }

    toggleListCommand({ mode, listStyle } = {}) {
        this.toggleList(mode, listStyle);
        this.dependencies.history.addStep();
    }

    getBlocksToToggleList() {
        const targetedBlocks = [...this.dependencies.selection.getTargetedBlocks()];
        return targetedBlocks.filter(
            (block) =>
                !descendants(block).some((descendant) =>
                    targetedBlocks.includes(descendant),
                ) &&
                block.isContentEditable &&
                !["OL", "UL"].includes(block.tagName),
        );
    }

    canToggleList(selection) {
        return this.canToggleListMemoized(selection);
    }

    /**
     * @param {string} mode
     * @param {string} [listStyle]
     * @throws {Error}
     */
    toggleList(mode, listStyle) {
        if (!["UL", "OL", "CL"].includes(mode)) {
            throw new Error(`Invalid list type: ${mode}`);
        }
        if (mode === "CL" && !!listStyle) {
            throw new Error(`listStyle is not compatible with "CL" list type`);
        }

        this.dependencies.split.splitBlockSegments();

        const sameModeListItems = new Set();
        const nonListBlocks = new Set();
        const listsToSwitch = new Set();
        for (const block of this.getBlocksToToggleList()) {
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
        const closestNestedLI = closestElement(root, "li:has(ul, ol)");
        if (closestNestedLI && closestNestedLI.closest("ul, ol")) {
            root = closestNestedLI.parentElement;
        }
        for (let element of selectElements(root, "ul, ol, li")) {
            if (isProtected(element) || isProtecting(element)) {
                continue;
            }
            for (const fn of [
                this.liWithoutParentToP,
                this.mergeSimilarLists,
                this.normalizeLI,
                this.normalizeNestedList,
            ]) {
                const updatedElement = fn.call(this, element);
                if (updatedElement) {
                    element = updatedElement;
                }
            }
        }
    }

    /**
     * @param {HTMLElement} element
     * @param {"UL"|"OL"|"CL"} mode
     */
    blockToList(element, mode) {
        if (element.matches(baseContainerGlobalSelector)) {
            return this.baseContainerToList(element, mode);
        }
        if (element.matches("td, th, li.nav-item, blockquote")) {
            return this.blockContentsToList(element, mode);
        }
        let list;
        const cursors = this.dependencies.selection.preserveSelection();
        if (element === this.editable) {
            const callingNode = element.firstChild;
            const group = getAdjacents(callingNode, (n) => !isBlock(n));
            list = insertListAfter(this.document, callingNode, mode, group);
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
     * @param {HTMLElement} baseContainer
     * @param {"UL"|"OL"|"CL"} mode
     */
    baseContainerToList(baseContainer, mode) {
        const cursors = this.dependencies.selection.preserveSelection();
        const list = insertListAfter(
            this.document,
            baseContainer,
            mode,
            childNodes(baseContainer),
        );
        const textAlign = baseContainer.style.getPropertyValue("text-align");
        if (textAlign) {
            list.firstElementChild.style.setProperty("text-align", textAlign);
            baseContainer.style.removeProperty("text-align");
        }
        this.dependencies.dom.copyAttributes(baseContainer, list);
        this.adjustListPadding(list);
        baseContainer.remove();
        cursors.remapNode(baseContainer, list.firstChild).restore();
        return list;
    }

    blockContentsToList(block, mode) {
        const cursors = this.dependencies.selection.preserveSelection();
        const list = insertListAfter(this.document, block.lastChild, mode, [
            ...block.childNodes,
        ]);
        cursors.remapNode(block, list.firstChild).restore();
        return list;
    }

    /**
     * @param {HTMLUListElement|HTMLOListElement|HTMLLIElement} node
     * @param {string} newMode
     * @returns {HTMLUListElement|HTMLOListElement|HTMLLIElement}
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

    /**
     * @param {HTMLElement} listContainerEl
     * @returns {"UL"|"OL"|"CL"|undefined}
     */
    getListMode(listContainerEl) {
        if (!["UL", "OL"].includes(listContainerEl.tagName)) {
            return;
        }
        if (listContainerEl.tagName === "OL") {
            return "OL";
        }
        return listContainerEl.classList.contains("o_checklist") ? "CL" : "UL";
    }

    /**
     * @param {HTMLOListElement|HTMLUListElement} list
     * @param {"UL"|"OL"|"CL"} newMode
     * @returns {HTMLOListElement|HTMLUListElement}
     */
    switchListMode(list, newMode) {
        if (this.getListMode(list) === newMode) {
            return;
        }
        const newTag = newMode === "CL" ? "UL" : newMode;
        const newList = this.dependencies.dom.setTagName(list, newTag);
        newList.style.removeProperty("list-style");
        for (const li of newList.children) {
            li.style.removeProperty("list-style");
            if (!isListElement(li.firstChild)) {
                li.classList.remove("oe-nested");
            }
        }
        removeClass(newList, "o_checklist");
        if (newMode === "CL") {
            newList.classList.add("o_checklist");
        }
        this.adjustListPadding(newList);
        return newList;
    }

    /**
     * @param {HTMLLIElement} li
     */
    liToBlocks(li) {
        while (li) {
            li = this.outdentLI(li);
        }
    }

    liWithoutParentToP(element) {
        const isOrphan = element.nodeName === "LI" && !element.closest("ul, ol");
        if (!isOrphan) {
            return;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        wrapInlinesInBlocks(element, {
            baseContainerNodeName: this.dependencies.baseContainer.getDefaultNodeName(),
            cursors,
        });
        cursors.update(callbacksForCursorUpdate.unwrap(element));
        unwrapContents(element);
        cursors.restore();
    }

    mergeSimilarLists(element) {
        if (
            !element.matches("ul, ol, li.oe-nested") ||
            (element.matches("li.oe-nested") && !element.querySelector("ul, ol"))
        ) {
            return;
        }
        const previousSibling = element.previousElementSibling;
        if (
            previousSibling &&
            element.isContentEditable &&
            previousSibling.isContentEditable &&
            (compareListTypes(previousSibling, element) ||
                (element.tagName === "LI" &&
                    isListItem(previousSibling) &&
                    isListElement(element.firstChild)))
        ) {
            const cursors = this.dependencies.selection.preserveSelection();
            cursors.update(callbacksForCursorUpdate.merge(element));
            previousSibling.append(...element.childNodes);
            element.remove();
            this.adjustListPadding(previousSibling);
            cursors.restore();
            return previousSibling;
        }
    }

    normalizeLI(element) {
        if (!isListItem(element)) {
            return;
        }

        if (
            element.firstChild?.nodeType === Node.ELEMENT_NODE &&
            isListElement(element.firstChild)
        ) {
            element.classList.add("oe-nested");
        }

        element.classList.toggle(
            "o_checked_has_nested_list",
            element.classList.contains("o_checked") &&
                !!element.querySelector("ul, ol"),
        );

        if (
            [...element.children].some(
                (child) =>
                    !isPhrasingContent(child) &&
                    !this.dependencies.split.isUnsplittable(child),
            )
        ) {
            const cursors = this.dependencies.selection.preserveSelection();
            wrapInlinesInBlocks(element, {
                baseContainerNodeName:
                    this.dependencies.baseContainer.getDefaultNodeName(),
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
            let li;
            if (element.previousElementSibling?.nodeName === "LI") {
                li = element.previousElementSibling;
            } else {
                li = this.document.createElement("li");
                li.classList.add("oe-nested");
            }
            element.parentElement.insertBefore(li, element);
            li.appendChild(element);
            cursors.restore();
        }
    }

    /**
     * @param {HTMLLIElement} li
     */
    indentLI(li) {
        const lip = li.previousElementSibling || this.document.createElement("li");
        if (!lip.hasChildNodes()) {
            lip.classList.add("oe-nested");
        }
        const parentLi = li.parentElement;
        const nextSiblingLi = li.nextSibling;
        const destul =
            li.previousElementSibling?.querySelector("ol, ul") ||
            li.querySelector("ol, ul") ||
            li.closest("ol, ul");
        const cursors = this.dependencies.selection.preserveSelection();
        parentLi.removeChild(li);
        const ul = createList(this.document, this.getListMode(destul));
        lip.append(ul);

        li.before(lip);
        ul.append(li);
        const nestedLists = childNodes(li).filter((n) => isListElement(n));
        ul.after(...nestedLists);
        parentLi.insertBefore(lip, nextSiblingLi);
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

    /**
     * @param {HTMLLIElement} li
     * @returns {HTMLLIElement|null}
     */
    outdentLI(li) {
        const listToSplit = li.querySelector("ol, ul") || li.nextElementSibling;
        if (listToSplit) {
            this.splitList(listToSplit);
        }

        if (isListItem(li.parentNode.parentNode)) {
            this.outdentNestedLI(li);
            return li;
        }
        this.outdentTopLevelLI(li);
        return null;
    }

    /**
     * @param {HTMLUListElement|HTMLOListElement|HTMLLIElement} node
     */
    splitList(node) {
        const cursors = this.dependencies.selection.preserveSelection();
        const currentList = closestElement(node, "ul, ol");
        const newList = currentList.cloneNode(false);
        const isList = isListElement(node);
        const wrapperLi = isList ? this.document.createElement("li") : node;

        if (isList) {
            wrapperLi.classList.add("oe-nested");
            newList.append(wrapperLi);
            cursors.update(
                callbacksForCursorUpdate.after(node.parentNode.parentNode, newList),
            );
            node.parentNode.parentNode.after(newList);
        } else if (isListItem(node.parentNode.parentNode)) {
            const lip = this.document.createElement("li");
            lip.classList.add("oe-nested");
            lip.append(newList);
            cursors.update(
                callbacksForCursorUpdate.after(node.parentNode.parentNode, lip),
            );
            node.parentNode.parentNode.after(lip);
        } else {
            cursors.update(callbacksForCursorUpdate.after(node.parentNode, newList));
            node.parentNode.after(newList);
        }

        const moveFrom = isList ? node.parentElement : node;
        while (moveFrom.nextSibling) {
            cursors.update(
                callbacksForCursorUpdate.append(newList, moveFrom.nextSibling),
            );
            newList.append(moveFrom.nextSibling);
        }

        const moveTo = isList ? wrapperLi : newList;
        cursors.update(callbacksForCursorUpdate.prepend(moveTo, node));
        moveTo.prepend(node);
        cursors.restore();
        this.adjustListPadding(currentList);
        this.adjustListPadding(newList);
        return newList;
    }

    outdentNestedLI(li) {
        const cursors = this.dependencies.selection.preserveSelection();
        const ul = li.parentNode;
        const lip = ul.parentNode;
        cursors.update(callbacksForCursorUpdate.after(lip, li));
        lip.after(li);
        while (ul.nextSibling) {
            cursors.update(callbacksForCursorUpdate.append(li, ul.nextSibling));
            li.append(ul.nextSibling);
        }
        if (!ul.children.length) {
            cursors.update(callbacksForCursorUpdate.remove(ul));
            ul.remove();
        }
        if (!lip.children.length && lip.classList.contains("oe-nested")) {
            cursors.update(callbacksForCursorUpdate.remove(lip));
            lip.remove();
        }
        this.adjustListPadding(li.parentElement);
        cursors.restore();
    }

    /**
     * @param {HTMLLIElement} li
     */
    outdentTopLevelLI(li) {
        const cursors = this.dependencies.selection.preserveSelection();
        const ul = li.parentNode;
        const children = childNodes(li);
        if (!children.every(isBlock)) {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            for (const child of children) {
                cursors.update(callbacksForCursorUpdate.append(baseContainer, child));
                baseContainer.append(child);
            }
            if (isShrunkBlock(baseContainer)) {
                baseContainer.append(this.document.createElement("br"));
            }
            li.append(baseContainer);
            cursors.remapNode(li, baseContainer);
        }
        const blocksToMove = childNodes(li);
        for (const block of blocksToMove.toReversed()) {
            cursors.update(callbacksForCursorUpdate.after(ul, block));
            ul.after(block);
        }
        const dir = li.getAttribute("dir") || ul.getAttribute("dir");
        const textAlign = li.style.getPropertyValue("text-align");
        const liColorStyle = getTextColorOrClass(li);
        const liFontSizeStyle = getFontSizeOrClass(li);
        const wrapChildren = (parent, tag) => {
            const wrapper = this.document.createElement(tag);
            wrapper.append(...parent.childNodes);
            parent.replaceChildren(wrapper);
            cursors.remapNode(parent, wrapper);
            return wrapper;
        };
        for (const block of blocksToMove) {
            if (dir && !block.getAttribute("dir")) {
                block.setAttribute("dir", dir);
            }
            if (textAlign && !block.style.getPropertyValue("text-align")) {
                block.style.setProperty("text-align", textAlign);
            }
            if (liColorStyle) {
                const font = wrapChildren(block, "font");
                this.dependencies.color.colorElement(font, liColorStyle.value, "color");
            }
            if (liFontSizeStyle && !isEmptyBlock(block)) {
                const span = wrapChildren(block, "span");
                if (liFontSizeStyle.type === "font-size") {
                    span.style.fontSize = liFontSizeStyle.value;
                } else if (liFontSizeStyle.type === "class") {
                    span.classList.add(liFontSizeStyle.value);
                }
            }
        }
        cursors.update(callbacksForCursorUpdate.remove(li));
        li.remove();
        if (!ul.firstElementChild) {
            cursors.update(callbacksForCursorUpdate.remove(ul));
            ul.remove();
        } else {
            this.adjustListPadding(ul);
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
        const blocks = [...this.dependencies.selection.getTargetedBlocks()].filter(
            (n) => !n.querySelector("li"),
        );
        for (const block of blocks) {
            const closestLI = block.closest("li");
            if (closestLI) {
                if (closestLI.classList.contains("nav-item")) {
                    navListItems.add(closestLI);
                } else if (closestLI.isContentEditable) {
                    listItems.add(closestLI);
                }
            } else if (!["UL", "OL"].includes(block.tagName)) {
                nonListItems.push(block);
            }
        }
        return {
            listItems: [...listItems],
            navListItems: [...navListItems],
            nonListItems,
        };
    }

    processNodeToInsert({ nodeToInsert, container }) {
        if (isListItemElement(container) && isParagraphRelatedElement(nodeToInsert)) {
            nodeToInsert = this.dependencies.dom.setTagName(nodeToInsert, "LI");
        }
        const listEl = container && closestElement(container, listElementSelector);
        if (!listEl) {
            return nodeToInsert;
        }
        const mode = container && this.getListMode(listEl);
        if (isListItemElement(nodeToInsert) && nodeToInsert.querySelector("ol, ul")) {
            return this.convertList(nodeToInsert, mode);
        }
        if (isListElement(nodeToInsert)) {
            return this.convertList(nodeToInsert, this.getListMode(nodeToInsert));
        }
        return nodeToInsert;
    }

    handleTab() {
        this.dependencies.split.splitBlockSegments();
        const selection = this.dependencies.selection.getEditableSelection();
        const closestLI = closestElement(selection.anchorNode, "LI");
        if (closestLI) {
            const block = closestBlock(selection.anchorNode);
            const isLiContainsUnSpittable =
                isParagraphRelatedElement(block) &&
                ancestors(block, closestLI).find((node) =>
                    this.dependencies.split.isUnsplittable(node),
                );
            if (isLiContainsUnSpittable) {
                return;
            }
        }
        const { listItems, navListItems, nonListItems } = this.separateListItems();
        if (listItems.length || navListItems.length) {
            this.indentListNodes(listItems);
            this.dependencies.tabulation.indentBlocks(nonListItems);
            const listsToAdjustPadding = new Set(
                listItems.map((li) => closestElement(li, "ul, ol")).filter(Boolean),
            );
            for (const list of listsToAdjustPadding) {
                this.adjustListPadding(list);
            }
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
                    this.dependencies.split.isUnsplittable(node),
                );
            if (isLiContainsUnSpittable) {
                return;
            }
        }
        const { listItems, navListItems, nonListItems } = this.separateListItems();
        if (listItems.length || navListItems.length) {
            this.outdentListNodes(listItems);
            this.dependencies.tabulation.outdentBlocks(nonListItems);
            this.dependencies.history.addStep();
            return true;
        }
    }

    handleSplitBlock(params) {
        const closestLI = closestElement(params.targetNode, "LI");
        const isBlockUnsplittable =
            closestLI &&
            Array.from(closestLI.childNodes).some(
                (node) => isBlock(node) && this.dependencies.split.isUnsplittable(node),
            );
        if (!closestLI || isBlockUnsplittable) {
            return;
        }
        if (isEmptyBlock(closestLI)) {
            this.outdentLI(closestLI);
            return true;
        }
        const [, newLI] = this.dependencies.split.splitElementBlock({
            ...params,
            blockToSplit: closestLI,
        });
        if (newLI) {
            if (closestLI.classList.contains("o_checked")) {
                removeClass(newLI, "o_checked");
            }
            const [anchorNode, anchorOffset] = getDeepestPosition(newLI, 0);
            this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
            this.adjustListPadding(newLI.parentElement);
        }
        return true;
    }

    handleDeleteBackward(range) {
        const { startContainer, startOffset, endContainer, endOffset } = range;
        const closestLIendContainer = closestElement(endContainer, "LI");
        if (!closestLIendContainer) {
            return;
        }
        const isCursorAtStartofLI =
            (startContainer === endContainer && startOffset === endOffset) ||
            closestElement(startContainer, "LI") !== closestLIendContainer;
        if (!isCursorAtStartofLI) {
            return;
        }
        let element = closestLIendContainer;
        while (["LI", "UL", "OL"].includes(element.tagName)) {
            if (this.dependencies.split.isUnsplittable(element)) {
                return;
            }
            element = element.parentElement;
        }
        if (!closestLIendContainer.classList.contains("oe-nested")) {
            closestLIendContainer.classList.add("oe-nested");
            closestLIendContainer.classList.remove("o_checked");
        } else {
            const list = closestElement(closestLIendContainer, "ul[dir], ol[dir]");
            const dir = list?.getAttribute("dir");
            if (dir) {
                closestLIendContainer.setAttribute("dir", dir);
            }
            this.liToBlocks(closestLIendContainer);
        }
        return true;
    }

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

    /**
     * @param {DocumentFragment} clonedContents
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     */
    processContentForClipboard(clonedContents, selection) {
        if (clonedContents.firstChild.nodeName === "LI") {
            const list = selection.commonAncestorContainer.cloneNode();
            list.replaceChildren(...childNodes(clonedContents));
            clonedContents = list;
        }
        return clonedContents;
    }

    insertListWithinPre(node) {
        const listItems = node.querySelectorAll("li:not(.oe-nested)");
        for (const li of listItems) {
            const nestingLvl = ancestors(li).filter(isListElement).length - 1;
            const list = closestElement(li, "ul, ol");
            const listMode = this.getListMode(list);
            let char;
            if (listMode === "CL") {
                char = "[] ";
            } else if (listMode === "OL") {
                const children = childNodes(li.parentElement).filter(
                    (n) => !n.classList.contains("oe-nested"),
                );
                char = `${children.indexOf(li) + 1}. `;
            } else {
                char = "* ";
            }
            const prefix = " ".repeat(nestingLvl * 4) + char;
            li.prepend(this.document.createTextNode(prefix));
        }
        return node;
    }

    /**
     * @param {MouseEvent | TouchEvent} ev
     */
    onPointerdown(ev) {
        const node = ev.target;
        const isChecklistItem =
            node.tagName === "LI" && this.getListMode(node.parentElement) === "CL";
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
            const { documentSelectionIsInEditable } =
                this.dependencies.selection.getSelectionData();
            if (!documentSelectionIsInEditable) {
                this.editable.focus();
                this.dependencies.selection.setSelection({
                    anchorNode: node,
                    anchorOffset: 0,
                });
            }
            ev.preventDefault();
            this.dependencies.history.addStep();
        }
    }

    handleTripleClick(ev) {
        const node = ev.target;
        const isChecklistItem =
            node.tagName === "LI" && this.getListMode(node.parentElement) === "CL";
        if (
            isChecklistItem &&
            this.isPointerInsideCheckbox(node, ev.offsetX, ev.offsetY)
        ) {
            return true;
        }
    }

    /**
     * @param {HTMLLIElement} li
     * @param {number} pointerOffsetX
     * @param {number} pointerOffsetY
     */
    isPointerInsideCheckbox(li, pointerOffsetX, pointerOffsetY) {
        const beforeStyle = this.window.getComputedStyle(li, ":before");
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

    applyColorToListItem(color, mode) {
        this.dependencies.split.splitSelection();
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        const listItems = new Set(
            targetedNodes.map((n) => closestElement(n, "li")).filter(Boolean),
        );
        if (!listItems.size || mode !== "color" || isColorGradient(color)) {
            return;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        for (const listItem of listItems) {
            removeEmptyTextNodes(listItem, cursors);

            if (this.dependencies.selection.areNodeContentsFullySelected(listItem)) {
                for (const node of [
                    listItem,
                    ...descendants(listItem).filter(
                        (n) => isElement(n) && closestElement(n, "LI") === listItem,
                    ),
                ]) {
                    const classesToRemove = [...node.classList].filter(
                        (cls) =>
                            cls === "o_default_color" || TEXT_CLASSES_REGEX.test(cls),
                    );
                    removeClass(node, ...classesToRemove);

                    if (node.style.color) {
                        removeStyle(node, "color");
                    }
                }

                if (color) {
                    this.dependencies.color.colorElement(listItem, color, mode);
                    const sublists = childNodes(listItem).filter(isListElement);
                    for (const list of sublists) {
                        list.classList.add("o_default_color");
                    }
                }
            } else if (
                color === "" &&
                (listItem.style.color ||
                    [...listItem.classList].some((cls) => TEXT_CLASSES_REGEX.test(cls)))
            ) {
                const textNodes = targetedNodes.filter(
                    (n) => isVisibleTextNode(n) && closestElement(n, "li") === listItem,
                );
                for (const node of textNodes) {
                    const font = this.document.createElement("font");
                    font.classList.add("o_default_color");
                    node.before(font);
                    cursors.update(callbacksForCursorUpdate.before(node, font));
                    font.append(node);
                    cursors.update(callbacksForCursorUpdate.append(font, node));
                }
            }
        }
        cursors.restore();
    }

    applyFormatToListItem(formatName, { formatProps, applyStyle } = {}) {
        if (!["setFontSizeClassName", "fontSize"].includes(formatName)) {
            return;
        }
        this.dependencies.split.splitSelection();
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        const listItems = new Set(
            targetedNodes.map((n) => closestElement(n, "li")).filter(Boolean),
        );
        if (!listItems.size) {
            return false;
        }
        const listsSet = new Set();
        const cursors = this.dependencies.selection.preserveSelection();
        for (const listItem of listItems) {
            const hasOnlyBaseBlocks = [...descendants(listItem)]
                .filter(isBlock)
                .every((n) => n.matches(`${baseContainerGlobalSelector}, ol, ul, li`));
            const hasExistingFontSize =
                FONT_SIZE_CLASSES.some((c) => listItem.classList.contains(c)) ||
                listItem.style.fontSize;
            if (!hasOnlyBaseBlocks || (!applyStyle && !hasExistingFontSize)) {
                continue;
            }

            removeEmptyTextNodes(listItem, cursors);

            if (this.dependencies.selection.areNodeContentsFullySelected(listItem)) {
                for (const node of [
                    listItem,
                    ...descendants(listItem).filter(
                        (n) => isElement(n) && closestElement(n, "LI") === listItem,
                    ),
                ]) {
                    removeClass(node, ...FONT_SIZE_CLASSES, "o_default_font_size");
                    if (node.style.fontSize) {
                        node.style.fontSize = "";
                    }
                }

                if (applyStyle) {
                    if (formatName === "setFontSizeClassName") {
                        listItem.classList.add(formatProps.className);
                    } else if (formatName === "fontSize") {
                        listItem.style.fontSize = formatProps.size;
                    }
                    const sublists = childNodes(listItem).filter(isListElement);
                    for (const list of sublists) {
                        list.classList.add("o_default_font_size");
                    }
                }
            } else if (!applyStyle && hasExistingFontSize) {
                const textNodes = targetedNodes.filter(
                    (n) => isVisibleTextNode(n) && closestElement(n, "li") === listItem,
                );
                for (const node of textNodes) {
                    const span = this.document.createElement("span");
                    span.classList.add("o_default_font_size");
                    node.before(span);
                    cursors.update(callbacksForCursorUpdate.before(node, span));
                    span.append(node);
                    cursors.update(callbacksForCursorUpdate.append(span, node));
                }
            }
            listsSet.add(listItem.parentElement);
        }
        cursors.restore();
        for (const list of listsSet) {
            this.adjustListPadding(list);
        }
        return true;
    }

    /**
     * @param {HTMLElement} li
     * @returns {number}
     */
    measureMarkerWidth(li) {
        const markerWidth = parseFloat(
            this.window.getComputedStyle(li, "::marker").width,
        );
        return isNaN(markerWidth) ? 0 : markerWidth;
    }

    /**
     * @param {HTMLElement} list
     */
    adjustListPadding(list) {
        if (!isListElement(list) || ![...list.children].some(getFontSizeOrClass)) {
            return;
        }
        list.style.removeProperty("padding-inline-start");
        if (list.classList.contains("o_checklist")) {
            return;
        }

        void list.offsetWidth;

        const largestMarker = list.children[Symbol.iterator]()
            .map((li) => this.measureMarkerWidth(li))
            .reduce((accumulator, currentValue) => Math.max(accumulator, currentValue));
        const largestMarkerPadding =
            Math.round(largestMarker) * (list.nodeName === "UL" ? 2 : 1);

        const defaultPadding = parseFloat(getHtmlStyle(this.document).fontSize) * 2;
        if (largestMarkerPadding > defaultPadding) {
            list.style.paddingInlineStart = `${largestMarkerPadding}px`;
        }
    }

    adjustListPaddingOnDelete() {
        const selection = this.document.getSelection();
        if (!selection.isCollapsed || !selection.anchorNode) {
            return;
        }
        const listItem = closestElement(selection.anchorNode);
        if (isListItem(listItem)) {
            this.adjustListPadding(listItem.parentElement);
        }
    }

    updateToolbarButtons() {
        this.toolbarListSelectorKey.value++;
    }

    getListSelectorButtons() {
        return listSelectorItems
            .filter(
                (item) =>
                    item.commandId !== "toggleListCL" || this.config.allowChecklist,
            )
            .map((item) => {
                const command = this.resources.user_commands.find(
                    (cmd) => cmd.id === item.commandId,
                );
                const button = composeToolbarButton(command, item);
                return {
                    ...pick(button, "id", "icon", "run", "mode"),
                    description: command.title,
                };
            });
    }

    handleInsert(container, block) {
        if (!this.config.allowChecklist) {
            for (const list of container.querySelectorAll(".o_checklist > li")) {
                this.liToBlocks(list);
            }
        }
        return container;
    }
}
