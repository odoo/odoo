import { getEmbeddedProps } from "@html_editor/others/embedded_component_utils";
import { Plugin } from "@html_editor/plugin";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock, isParagraphRelatedElement } from "@html_editor/utils/dom_info";
import {
    childNodes,
    children,
    closestElement,
    firstLeaf,
    lastLeaf,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { childNodeIndex, nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";
import { uuid } from "@web/core/utils/strings";

const toggleSelector = "[data-embedded='toggleBlock']";
const titleSelector = "[data-embedded-editable='title']";
const contentSelector = "[data-embedded-editable='content']";

export class ToggleBlockPlugin extends Plugin {
    static id = "toggleBlock";
    static dependencies = [
        "baseContainer",
        "delete",
        "dom",
        "embeddedComponents", // toggle is an embedded component.
        "history",
        "selection",
        "split",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        hints: [
            withSequence(20, {
                selector: `${toggleSelector} ${titleSelector} > *`,
                text: _t("Toggle title"),
            }),
            withSequence(10, {
                selector: `${toggleSelector} ${contentSelector}:not(:focus) > ${baseContainerGlobalSelector}:only-child`,
                text: _t("Add something inside this toggle"),
            }),
        ],
        hint_targets_providers: (selectionData, editable) => [
            ...editable.querySelectorAll(
                `${toggleSelector} ${contentSelector} > ${baseContainerGlobalSelector}:only-child`
            ),
        ],
        move_node_blacklist_selectors: `${toggleSelector} ${titleSelector} *`,
        selection_blocker_predicates: (blocker) => {
            // Prevent the insertion of selection placeholders around toggle blocks.
            if (blocker.nodeType === Node.ELEMENT_NODE && blocker.dataset.embedded === "toggleBlock") {
                return false;
            }
        },
        powerbox_items: [
            {
                commandId: "insertToggleBlock",
                categoryId: "structure",
            },
        ],
        shortcuts: [{ hotkey: "control+enter", commandId: "switchToggleBlockState" }],
        user_commands: [
            {
                id: "insertToggleBlock",
                title: _t("Toggle list"),
                description: _t("Hide Text under foldable toggles"),
                icon: "fa-caret-square-o-right",
                isAvailable: (selection) =>
                    isHtmlContentSupported(selection) &&
                    !closestElement(selection.anchorNode, `${toggleSelector} ${titleSelector}`),
                run: () => {
                    this.insertToggleBlock();
                },
            },
            {
                id: "switchToggleBlockState",
                run: this.manageToggleFromTitle.bind(this),
            },
        ],

        normalize_handlers: withSequence(Infinity, this.normalize.bind(this)),

        delete_backward_overrides: this.handleDeleteBackward.bind(this),
        delete_forward_overrides: this.handleDeleteForward.bind(this),
        shift_tab_overrides: this.handleShiftTab.bind(this),
        split_element_block_overrides: withSequence(1, this.handleSplitElementBlock.bind(this)),
        tab_overrides: this.handleTab.bind(this),

        power_buttons_visibility_predicates: this.showPowerButtons.bind(this),

        before_insert_processors: this.handleInsert.bind(this),
    };

    setup() {
        this.preventDeleteBackwardContentEnd = false;
        this.selectedToggleEmptyContentSet = new Set();
    }

    explodeToggle(toggle) {
        const title = toggle.querySelector(titleSelector);
        const content = toggle.querySelector(contentSelector);
        let contentChildren = children(content);
        if (contentChildren.length === 1 && isEmptyBlock(contentChildren[0])) {
            contentChildren = [];
        }
        toggle.replaceWith(...children(title), ...contentChildren);
    }

    forceToggle(toggle, { showContent, restoreSelection } = {}) {
        toggle.dispatchEvent(
            new CustomEvent("forceToggle", { detail: { showContent, restoreSelection } })
        );
    }

    generateUniqueIds(toggles) {
        for (const toggle of toggles) {
            const props = getEmbeddedProps(toggle);
            props.toggleBlockId = this.getUniqueIdentifier();
            toggle.dataset.embeddedProps = JSON.stringify(props);
        }
    }

    getClosestToggleContentInfo(node) {
        const toggle = closestElement(node, toggleSelector);
        const title = toggle?.querySelector(titleSelector);
        const content = toggle?.querySelector(contentSelector);
        return content?.contains(node) ? { content, title, toggle } : {};
    }

    getClosestToggleTitleInfo(node) {
        const toggle = closestElement(node, toggleSelector);
        const title = toggle?.querySelector(titleSelector);
        const content = toggle?.querySelector(contentSelector);
        return title?.contains(node) ? { content, title, toggle } : {};
    }

    getToggleFromTitleSelection() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (!selection.anchorNode) {
            return;
        }
        const { toggle } = this.getClosestToggleTitleInfo(selection.anchorNode);
        return toggle;
    }

    getUniqueIdentifier() {
        return uuid();
    }

    /**
     * Handle all behaviors linked to the use of deleteBackward in the editor:
     * 1. selection at start of title: explode the toggle and keep title and content as siblings
     * 2. selection at end of content in a paragraph: unwraps from the toggle content
     * 3. selection at start of content in a paragraph: merge the paragraph with the title
     * 4. selection at start of paragraph after a toggle: merge the paragraph at content end
     */
    handleDeleteBackward(range) {
        for (const handler of [
            this.handleDeleteBackwardTitleStart,
            this.handleDeleteBackwardContentEnd,
            this.handleDeleteBackwardContentStart,
            this.handleDeleteBackwardAfterToggle,
        ]) {
            if (handler.call(this, range)) {
                return true;
            }
        }
    }

    handleDeleteBackwardContentEnd({ endContainer, endOffset }) {
        const block = closestBlock(endContainer);
        const isEmptyContainer = isEmptyBlock(endContainer);
        const leaf = isEmptyContainer ? endContainer : firstLeaf(block);
        const { toggle, content } = this.getClosestToggleContentInfo(endContainer);
        if (
            !content ||
            endOffset !== 0 ||
            childNodeIndex(block) === 0 ||
            block.nextElementSibling ||
            leaf !== endContainer ||
            !isParagraphRelatedElement(block) ||
            this.preventDeleteBackwardContentEnd
        ) {
            return;
        }
        toggle.after(block);
        this.dependencies.selection.setCursorStart(block);
        return true;
    }

    handleDeleteBackwardContentStart({ endContainer, endOffset }) {
        const block = closestBlock(endContainer);
        const leaf = isEmptyBlock(endContainer) ? endContainer : firstLeaf(block);
        const { title, content } = this.getClosestToggleContentInfo(endContainer);
        if (
            !content ||
            endOffset !== 0 ||
            childNodeIndex(block) !== 0 ||
            leaf !== endContainer ||
            !isParagraphRelatedElement(block)
        ) {
            return;
        }
        title.append(block);
        this.dependencies.selection.setCursorStart(block);
        this.dependencies.delete.deleteBackward(
            this.dependencies.selection.getEditableSelection(),
            "character"
        );
        return true;
    }

    handleDeleteBackwardTitleStart({ endContainer, endOffset }) {
        const block = closestBlock(endContainer);
        const leaf = isEmptyBlock(endContainer) ? endContainer : firstLeaf(block);
        const { toggle, title } = this.getClosestToggleTitleInfo(endContainer);
        if (!title || endOffset !== 0 || childNodeIndex(block) !== 0 || leaf !== endContainer) {
            return;
        }
        const cursors = this.dependencies.selection.preserveSelection();
        this.explodeToggle(toggle);
        cursors.restore();
        return true;
    }

    handleDeleteBackwardAfterToggle({ endContainer, endOffset }) {
        const block = closestBlock(endContainer);
        const leaf = isEmptyBlock(endContainer) ? endContainer : firstLeaf(block);
        const toggle = block?.previousSibling;
        if (!toggle?.matches?.(toggleSelector) || endOffset !== 0 || leaf !== endContainer) {
            return;
        }
        let target = toggle.querySelector(contentSelector);
        if (target.parentElement.matches(".d-none")) {
            if (!isParagraphRelatedElement(block)) {
                return;
            }
            const title = toggle.querySelector(titleSelector);
            target = title;
        }
        target.append(block);
        this.dependencies.selection.setCursorStart(block);
        this.preventDeleteBackwardContentEnd = true;
        this.dependencies.delete.deleteBackward(
            this.dependencies.selection.getEditableSelection(),
            "character"
        );
        this.preventDeleteBackwardContentEnd = false;
        return true;
    }

    /**
     * Handle all behaviors linked to the use of deleteForward in the editor:
     * 1. selection at end of title:
     *   - (optional) explode a potential toggle at the start of content
     *   - merge first paragraph from content with the title
     * 2. selection at end of content in a paragraph:
     *   - (optional) explode a potential sibling toggle
     *   - merge a sibling paragraph at content end
     * 3. selection at end of paragraph before a toggle: explode the toggle
     */
    handleDeleteForward(range) {
        for (const handler of [
            this.handleDeleteForwardTitleEnd,
            this.handleDeleteForwardContentEnd,
            this.handleDeleteForwardBeforeToggle,
        ]) {
            if (handler.call(this, range)) {
                return true;
            }
        }
    }

    handleDeleteForwardContentEnd({ startContainer, startOffset }) {
        const block = closestBlock(startContainer);
        const isEmptyContainer = isEmptyBlock(startContainer);
        const leaf = isEmptyContainer ? startContainer : lastLeaf(block);
        const { toggle, content } = this.getClosestToggleContentInfo(startContainer);
        if (
            !content ||
            !(
                (isEmptyContainer && startOffset === 0) ||
                startOffset === nodeSize(startContainer)
            ) ||
            block === this.editable ||
            block.nextElementSibling ||
            leaf !== startContainer ||
            !isParagraphRelatedElement(block)
        ) {
            return;
        }
        let nextEl = toggle.nextSibling;
        if (nextEl?.matches?.(toggleSelector)) {
            this.explodeToggle(nextEl);
            nextEl = toggle.nextSibling;
        }
        if (!isParagraphRelatedElement(nextEl)) {
            return;
        }
        content.append(nextEl);
        this.dependencies.selection.setCursorEnd(block);
        this.dependencies.delete.deleteForward(
            this.dependencies.selection.getEditableSelection(),
            "character"
        );
        return true;
    }

    handleDeleteForwardTitleEnd({ startContainer, startOffset }) {
        const block = closestBlock(startContainer);
        const isEmptyContainer = isEmptyBlock(startContainer);
        const leaf = isEmptyContainer ? startContainer : lastLeaf(block);
        const { toggle, title, content } = this.getClosestToggleTitleInfo(startContainer);
        if (
            !title ||
            !(
                (isEmptyContainer && startOffset === 0) ||
                startOffset === nodeSize(startContainer)
            ) ||
            block === this.editable ||
            block.nextElementSibling ||
            leaf !== startContainer
        ) {
            return;
        }
        let nextEl;
        if (content.parentElement.matches(".d-none")) {
            nextEl = toggle.nextSibling;
            if (nextEl.matches?.(toggleSelector)) {
                this.explodeToggle(nextEl);
                nextEl = toggle.nextSibling;
            }
        } else {
            nextEl = content.firstChild;
            if (nextEl.matches?.(toggleSelector)) {
                this.explodeToggle(nextEl);
                nextEl = content.firstChild;
            }
        }
        if (!isParagraphRelatedElement(nextEl)) {
            return;
        }
        title.append(nextEl);
        this.dependencies.selection.setCursorEnd(block);
        this.dependencies.delete.deleteForward(
            this.dependencies.selection.getEditableSelection(),
            "character"
        );
        return true;
    }

    handleDeleteForwardBeforeToggle({ startContainer, startOffset }) {
        const block = closestBlock(startContainer);
        const isEmptyContainer = isEmptyBlock(startContainer);
        const leaf = isEmptyContainer ? startContainer : lastLeaf(block);
        const toggle = block.nextSibling;
        if (
            !toggle?.matches?.(toggleSelector) ||
            !(
                (isEmptyContainer && startOffset === 0) ||
                startOffset === nodeSize(startContainer)
            ) ||
            leaf !== startContainer
        ) {
            return;
        }
        if (isEmptyBlock(block)) {
            block.remove();
            const title = toggle.querySelector(titleSelector);
            this.dependencies.selection.setCursorStart(title.firstElementChild);
        } else {
            this.explodeToggle(toggle);
            this.dependencies.selection.setCursorEnd(block);
            this.dependencies.delete.deleteForward(
                this.dependencies.selection.getEditableSelection(),
                "character"
            );
        }
        return true;
    }

    /**
     * Generate new toggleBlockIds for every inserted toggle, to avoid duplicating
     * copies.
     */
    handleInsert(insertContainer) {
        const insertedToggles = insertContainer.querySelectorAll(toggleSelector);
        this.generateUniqueIds(insertedToggles);
        return insertContainer;
    }

    /**
     * Shift + Tab in a toggle title will extract it from a potential parent
     * toggle, and every child of that parent toggle content that is a nextSibling
     * of the current toggle will be appended to the current toggle content.
     */
    handleShiftTab() {
        const toggle = this.getToggleFromTitleSelection();
        if (toggle) {
            const closestToggleAncestor = closestElement(toggle.parentElement, toggleSelector);
            if (closestToggleAncestor) {
                const cursors = this.dependencies.selection.preserveSelection();
                const ancestorContent = closestToggleAncestor.querySelector(contentSelector);
                const containerContent = toggle.querySelector(contentSelector);
                const siblings = childNodes(ancestorContent).filter(
                    (node) =>
                        toggle.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING
                );
                if (isEmptyBlock(containerContent.lastElementChild)) {
                    containerContent.lastElementChild.remove();
                }
                containerContent.append(...siblings);
                closestToggleAncestor.after(toggle);
                this.forceToggle(toggle, { showContent: true, restoreSelection: cursors.restore });
                this.dependencies.history.addStep();
            }
            return true;
        }
    }

    /**
     * This method handles the behavior when the user presses the Enter key.
     * In the editor, when the user presses the Enter key, this splits the focused text block into 2
     * separate ones. When the text block is split then it calls to all handlers so that they can trigger
     * a specific behavior with the split block.
     *
     * This handler handles multiple cases:
     *      1. The toggle title is currently empty (remove toggle)
     *      2. Cursor is at the start of the toggle title (create new toggle before)
     *      3. Cursor elsewhere in the toggle title (create new toggle after)
     * @param {Object} param @see SplitPlugin.splitElementBlock
     * @returns true if indeed handled by the method
     */
    handleSplitElementBlock({ targetNode, targetOffset, blockToSplit }) {
        const { toggle, title, content } = this.getClosestToggleTitleInfo(targetNode);
        if (title) {
            const selection = this.dependencies.selection.getEditableSelection();
            if (isEmptyBlock(selection.anchorNode)) {
                const contentChildren = children(content);
                if (contentChildren.length !== 1 || !isEmptyBlock(contentChildren[0])) {
                    toggle.after(...children(content));
                }
                const baseContainer = this.dependencies.baseContainer.createBaseContainer();
                baseContainer.appendChild(this.document.createElement("br"));
                toggle.replaceWith(baseContainer);
                this.dependencies.selection.setCursorStart(baseContainer);
                return true;
            }
            const insertBefore = targetOffset === 0 && blockToSplit.parentElement === title;
            const [beforeSplit, afterSplit] = this.dependencies.split.splitElementBlock({
                targetNode,
                targetOffset,
                blockToSplit,
            });
            if (beforeSplit && afterSplit) {
                if (content.parentElement.matches(".d-none") || insertBefore) {
                    const newToggle = this.renderToggleBlock();
                    const newToggleBlock = newToggle.querySelector(toggleSelector);
                    const newTitleEl = newToggle.querySelector(titleSelector);
                    const dir = toggle.getAttribute("dir");
                    if (dir) {
                        newToggleBlock.setAttribute("dir", dir);
                    }
                    if (insertBefore) {
                        toggle.before(newToggle);
                        newTitleEl.replaceChildren(beforeSplit);
                    } else {
                        toggle.after(newToggle);
                        newTitleEl.replaceChildren(afterSplit);
                    }
                } else {
                    const firstChild = content.firstElementChild;
                    if (isEmptyBlock(firstChild)) {
                        firstChild.replaceWith(afterSplit);
                    } else {
                        content.prepend(afterSplit);
                    }
                }
                this.dependencies.selection.setCursorStart(afterSplit);
            }
            return true;
        }
    }

    /**
     * Handles the tab behavior. This means that when we are inside a toggle title and we have a toggle
     * as previous sibling of the embedded component, the current toggle is indented inside the content of
     * the previous one.
     */
    handleTab() {
        const toggle = this.getToggleFromTitleSelection();
        if (toggle) {
            const previousSibling = toggle.previousSibling;
            if (previousSibling?.matches?.(toggleSelector)) {
                const cursors = this.dependencies.selection.preserveSelection();
                const previousSiblingContent = previousSibling.querySelector(contentSelector);
                if (
                    children(previousSiblingContent).length === 1 &&
                    isEmptyBlock(previousSiblingContent.firstElementChild)
                ) {
                    previousSiblingContent.replaceChildren(toggle);
                } else {
                    previousSiblingContent.append(toggle);
                }
                const content = toggle.querySelector(contentSelector);
                if (!content.parentElement.matches(".d-none")) {
                    toggle.after(...children(content));
                }
                this.forceToggle(previousSibling, {
                    showContent: true,
                    restoreSelection: cursors.restore,
                });
                this.dependencies.history.addStep();
            }
            return true;
        }
    }

    insertToggleBlock() {
        const block = this.renderToggleBlock();
        const target = block.querySelector(`${titleSelector} > ${baseContainerGlobalSelector}`);
        this.dependencies.dom.insert(block);
        this.dependencies.selection.setCursorStart(target);
        this.dependencies.history.addStep();
    }

    manageToggleFromTitle() {
        const toggle = this.getToggleFromTitleSelection();
        if (!toggle) {
            return;
        }
        this.forceToggle(toggle);
    }

    normalize(element) {
        const cursors = this.dependencies.selection.preserveSelection();
        let shouldRestoreCursor = false;
        for (const titleChild of selectElements(
            element,
            `${toggleSelector} ${titleSelector} > *:first-child`
        )) {
            const title = titleChild.parentElement;
            const toggle = closestElement(title, toggleSelector);
            if (titleChild.nextElementSibling) {
                const nodes = children(titleChild.parentElement);
                title.replaceChildren(nodes.shift());
                toggle.after(...nodes);
                shouldRestoreCursor = true;
            }
            if (!isParagraphRelatedElement(titleChild)) {
                toggle.after(titleChild);
                shouldRestoreCursor = true;
            }
        }
        if (shouldRestoreCursor) {
            cursors.restore();
        }
        for (const emptyToggleNode of selectElements(
            element,
            `${toggleSelector} [data-embedded-editable]:empty`
        )) {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.appendChild(this.document.createElement("br"));
            emptyToggleNode.replaceChildren(baseContainer);
        }
    }

    renderToggleBlock() {
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        return parseHTML(
            this.document,
            renderToString("html_editor.EmbeddedToggleBlockBlueprint", {
                baseContainerNodeName: baseContainer.nodeName,
                baseContainerAttributes: {
                    class: baseContainer.className,
                },
                embeddedProps: JSON.stringify({ toggleBlockId: this.getUniqueIdentifier() }),
            })
        );
    }

    showPowerButtons(selection) {
        return (
            selection.isCollapsed &&
            !closestElement(selection.anchorNode, `${toggleSelector} ${titleSelector}`)
        );
    }
}
