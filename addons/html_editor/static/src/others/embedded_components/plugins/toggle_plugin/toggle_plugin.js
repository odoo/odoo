import { Plugin } from "@html_editor/plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock, isTextNode, paragraphRelatedElements } from "@html_editor/utils/dom_info";
import {
    children,
    closestElement,
    findFurthest,
    firstLeaf,
} from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";
import { renderToString } from "@web/core/utils/render";
import { uuid } from "@web/views/utils";

const titleSelector = "[data-embedded='toggle'] [data-embedded-editable='title']";
const contentSelector = "[data-embedded='toggle'] [data-embedded-editable='content']";

export class TogglePlugin extends Plugin {
    static id = "toggle_list";
    static dependencies = ["list", "history", "embeddedComponents", "dom", "selection"];
    resources = {
        user_commands: [
            {
                id: "insertToggleList",
                title: _t("Toggle List"),
                description: _t("Hide Text under a Toggle"),
                icon: "fa-caret-square-o-right",
                isAvailable: (node) => !closestElement(node, titleSelector),
                run: () => {
                    this.insertToggleList();
                },
            },
        ],
        powerbox_items: [
            {
                commandId: "insertToggleList",
                categoryId: "structure",
            },
        ],
        normalize_handlers: this.normalize.bind(this),
        delete_backward_overrides: this.handleDeleteBackward.bind(this),
        delete_forward_overrides: this.handleDeleteForward.bind(this),
        tab_overrides: this.handleTab.bind(this),
        shift_tab_overrides: this.handleShiftTab.bind(this),
        hints: [
            withSequence(1, {
                selector: `${titleSelector} > *`,
                text: "Toggle Title",
            }),
            withSequence(2, {
                selector: `${contentSelector} > p:only-child`,
                text: "This is empty, add some text",
            }),
        ],
        split_element_block_overrides: withSequence(1, this.handleSplitElementBlock.bind(this)),
        power_buttons_visibility_predicates: this.showPowerButtons.bind(this),
        before_paste_handlers: this.beforePaste.bind(this),
        disallowed_list_selectors: `${titleSelector} *, div.collapsed > [data-embedded-editable='content'] *`,
        mount_component_handlers: this.setupNewToggle.bind(this),
        select_all_handlers: this.selectAll.bind(this),
    };

    setup() {
        const allToggles = this.editable.querySelectorAll("[data-embedded='toggle']");
        allToggles.forEach((toggleNode) => {
            this.addDomListener(toggleNode, "keydown", (ev) => {
                if (["arrowup", "arrowdown"].includes(getActiveHotkey(ev))) {
                    this.handleKeyDown(ev);
                }
            });
        });
    }

    selectAll() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (closestElement(selection.anchorNode, "[data-embedded='toggle']")) {
            const node = findFurthest(
                selection.anchorNode,
                this.editable,
                (element) => element.dataset.embedded === "toggle"
            );
            if (node) {
                this.dependencies.selection.setSelection({
                    anchorNode: node.previousSibling || node,
                    anchorOffset: 0,
                });
            }
        }
    }

    handleKeyDown(ev) {
        const selection = this.dependencies.selection.getEditableSelection();
        const targetEl = closestBlock(selection.anchorNode);
        if (targetEl.previousSibling && targetEl.nextSibling) {
            return;
        }
        if (getActiveHotkey(ev) === "arrowup" && !targetEl.previousSibling) {
            this._arrowUp(selection);
            ev.preventDefault();
            ev.stopImmediatePropagation();
        } else if (getActiveHotkey(ev) === "arrowdown" && !targetEl.nextSibling) {
            this._arrowDown(selection);
            ev.preventDefault();
            ev.stopImmediatePropagation();
        }
    }

    _arrowUp(selection) {
        const container = closestElement(selection.anchorNode, "[data-embedded-editable]");
        let previous;
        let anchorNode;
        if (container.dataset.embeddedEditable === "content") {
            previous = container.parentElement.previousSibling;
            anchorNode = firstLeaf(
                previous.querySelector("[data-embedded-editable='title']"),
                isTextNode
            );
        } else {
            previous = closestElement(container, "[data-embedded]").previousSibling;
            anchorNode = firstLeaf(
                previous.dataset.embedded === "toggle"
                    ? previous.querySelector(
                          ".o_embedded_toggle_button:has(.fa-caret-right) + div [data-embedded-editable='title'], [data-embedded-editable='content']"
                      )
                    : previous,
                isTextNode
            );
        }
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset: Math.min(selection.anchorOffset, anchorNode.textContent.length),
        });
    }

    _arrowDown(selection) {
        const container = closestElement(selection.anchorNode, "[data-embedded-editable]");
        let next;
        let anchorNode;
        if (
            container.dataset.embeddedEditable === "title" &&
            container.parentElement.previousSibling.querySelector(".fa-caret-down")
        ) {
            next = container.parentElement.parentElement.nextSibling;
            anchorNode = firstLeaf(
                next,
                (node) => closestElement(node, "[data-embedded-editable]") && isTextNode(node)
            );
        } else {
            next = closestElement(
                container,
                (element) => element.dataset.embedded === "toggle" && element.nextSibling
            ).nextSibling;
            anchorNode = firstLeaf(
                next.dataset.embedded === "toggle"
                    ? next.querySelector("[data-embedded-editable='title']")
                    : next,
                isTextNode
            );
        }
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset: Math.min(selection.anchorOffset, anchorNode.textContent.length),
        });
    }

    showPowerButtons(selection) {
        return selection.isCollapsed && !closestElement(selection.anchorNode, titleSelector);
    }

    setupNewToggle({ name, env }) {
        if (name === "toggle") {
            Object.assign(env, {
                editorShared: {
                    preserveSelection: this.dependencies.selection.preserveSelection,
                },
            });
        }
    }

    normalize(element) {
        const toggleNodes = element.querySelectorAll("[data-embedded='toggle']");
        for (const toggleNode of toggleNodes) {
            const target = toggleNode.querySelector("[data-embedded-editable]:empty");
            if (target) {
                const newParagraph = this.document.createElement("p");
                newParagraph.appendChild(this.document.createElement("br"));
                target.replaceChildren(newParagraph);
            }
        }
    }

    beforePaste(selection, ev) {
        const { anchorNode } = selection;
        const closestToggleTitle = closestElement(anchorNode, titleSelector);
        if (!closestToggleTitle) {
            return;
        }
        const fragmentToCheck = parseHTML(this.document, ev.clipboardData.getData("text/html"));
        if (fragmentToCheck.childNodes.length === 1) {
            if (fragmentToCheck.childNodes[0].nodeType === Node.TEXT_NODE) {
                return;
            }
            const nodes = Array.from([
                ...fragmentToCheck.children[0].querySelectorAll("*"),
                fragmentToCheck.children[0],
            ]);
            if (nodes.every((node) => paragraphRelatedElements.includes(node.tagName))) {
                return;
            }
        }
        // new paragraph after toggle
        const newParagraph = this.document.createElement("p");
        const [node, offset] = rightPos(closestToggleTitle.closest("[data-embedded]"));
        this.dependencies.selection.setSelection({
            anchorNode: node,
            anchorOffset: offset,
        });
        // setSelection in newParagraph
        this.dependencies.dom.insert(newParagraph);
        this.dependencies.selection.setCursorStart(newParagraph);
    }

    getUniqueIdentifier() {
        return uuid();
    }

    insertToggleList() {
        const block = parseHTML(
            this.document,
            renderToString("html_editor.ToggleBlueprint", {
                embeddedProps: JSON.stringify({ toggleId: this.getUniqueIdentifier() }),
            })
        );
        const target = block.querySelector("[data-embedded-editable='title'] > p");
        this.dependencies.dom.insert(block);
        this.addDomListener(block, "keydown", (ev) => {
            if (["arrowup", "arrowdown"].includes(getActiveHotkey(ev))) {
                this.handleKeyDown(ev);
            }
        });
        this.dependencies.selection.setCursorStart(target);
        this.dependencies.history.addStep();
    }

    handleDeleteForward(range) {
        const { startContainer, startOffset, endContainer, endOffset } = range;
        const closestToggleTitle = closestElement(startContainer, titleSelector);
        if (!closestToggleTitle) {
            return;
        }
        const isCursorAtStartofTitle =
            (startContainer === endContainer && startOffset === endOffset) ||
            closestElement(startContainer, titleSelector) !== closestToggleTitle;
        if (!isCursorAtStartofTitle) {
            return;
        }
        const container = closestToggleTitle.closest("[data-embedded]");
        const nextSibling = container.nextElementSibling;
        if (nextSibling.closest("[data-embedded='toggle']") === nextSibling) {
            const cursors = this.dependencies.selection.preserveSelection();
            const nextTitle = nextSibling.querySelector("[data-embedded-editable='title']");
            const nextContent = nextSibling.querySelector("[data-embedded-editable='content']");
            const right = rightPos(nextSibling);
            this.dependencies.selection.setSelection({
                anchorNode: right[0],
                anchorOffset: right[1],
                focusNode: right[0],
                focusOffset: right[1],
            });
            const fragment = this.document.createDocumentFragment();
            let childrenToInsert = children(nextContent);
            if (childrenToInsert.length === 1 && isEmptyBlock(childrenToInsert[0])) {
                childrenToInsert = [];
            }
            fragment.replaceChildren(...childrenToInsert);
            if (fragment.children.length !== 0) {
                this.dependencies.dom.insert(fragment);
            }
            closestToggleTitle
                .querySelector("p")
                .insertBefore(
                    this.document.createTextNode(nextTitle.textContent),
                    closestToggleTitle.querySelector("p").lastChild
                );
            nextSibling.remove();
            cursors.restore();
        }
        return true;
    }

    /**
     * Handles all the behaviors linked to the use of deleteBackward in the editor.
     * We need to handle some specific behaviors:
     *  1. When we aren't in a toggle title but the previous element is a toggle. (opened and closed)
     *  2. When we are at the start of the title and we have nothing above the current embedded toggle.
     * @param {Object} range
     */
    handleDeleteBackward(range) {
        // startContainer should be the editable to indicate the start of the block.
        const { startContainer, startOffset, endOffset } = range;
        // endContainer represents the block where the cursor is.
        const endContainer = closestElement(range.endContainer, isBlock);
        const closestToggleTitle = closestElement(startContainer, titleSelector);
        // We are at the start if either we have the same end and start container and the same offset (in title).
        // Or if the startContainer is the editable with an endOffset of 0 (in the editable).
        const isCursorAtStart =
            (closestElement(startContainer) === closestElement(endContainer) &&
                startOffset === endOffset) ||
            (startContainer === closestElement(endContainer, "[contenteditable='true']") &&
                endOffset === 0);
        if (isCursorAtStart && endContainer.previousElementSibling?.dataset.embedded === "toggle") {
            // If we are inside the editor after an embedded toggle. We set the cursor to the end
            // of either the title or the last paragraph of the content.
            this.dependencies.selection.setCursorEnd(
                endContainer.previousElementSibling.querySelector(
                    ".btn:has(.fa-caret-right) + div > [data-embedded-editable='title'] > *, [data-embedded-editable='content'] > p:last-of-type"
                )
            );
            if (!endContainer.textContent) {
                // If the paragraph we are leaving is empty we remove it to follow the classic
                // deleteBackwards behavior.
                endContainer.remove();
            } else {
                const { anchorNode } = this.dependencies.selection.getEditableSelection();
                const { restore: restoreSelection } =
                    this.dependencies.selection.preserveSelection();
                if (closestElement(anchorNode, contentSelector)) {
                    this.dependencies.dom.insert(endContainer);
                } else {
                    const titleContainer = closestElement(anchorNode, titleSelector);
                    titleContainer.firstChild.after(range.endContainer);
                }
                restoreSelection();
            }
            return true;
        }
        if (!closestToggleTitle) {
            return;
        }
        const isCursorAtStartofTitle =
            isCursorAtStart || closestElement(startContainer, titleSelector) !== closestToggleTitle;
        if (!isCursorAtStartofTitle) {
            return;
        }
        const container = closestToggleTitle.closest("[data-embedded]");
        const newParagraph = this.document.createElement("p");
        newParagraph.textContent = closestToggleTitle.textContent || "";
        if (!newParagraph.textContent) {
            newParagraph.appendChild(this.document.createElement("br"));
        }
        const contentToInsert = container.querySelectorAll(`${contentSelector} > *`);
        if (contentToInsert.length > 1 || !isEmptyBlock(contentToInsert[0])) {
            const right = rightPos(container);
            this.dependencies.selection.setSelection({
                anchorNode: right[0],
                anchorOffset: right[1],
                focusNode: right[0],
                focusOffset: right[1],
            });
            const fragment = this.document.createDocumentFragment();
            fragment.replaceChildren(...contentToInsert);
            this.dependencies.dom.insert(fragment);
        }
        container.replaceWith(newParagraph);
        this.dependencies.history.addStep();
        this.dependencies.selection.setCursorStart(newParagraph);
        return true;
    }

    /**
     * Handles the tab behavior. This means that when we are inside a toggle title and we have a toggle
     * as previous sibling of the embedded component, the current toggle is indented inside the content of
     * the previous one.
     */
    handleTab() {
        const selection = this.dependencies.selection.getEditableSelection();
        const closestToggleTitle = closestElement(selection.anchorNode, titleSelector);
        if (closestToggleTitle) {
            // If selection is in a title.
            const container = closestToggleTitle.closest("[data-embedded]");
            const previousSibling = container.previousElementSibling;
            if (previousSibling?.closest("[data-embedded='toggle']") === previousSibling) {
                // If the previous element of the embedded component is also a toggle, we need to handle
                // it.
                const cursors = this.dependencies.selection.preserveSelection();
                this.dependencies.selection.setCursorEnd(
                    previousSibling.querySelector("[data-embedded-editable='content']")
                );
                previousSibling.firstChild.querySelector("i.fa-caret-right")?.click(); // open the toggle if needed
                const fragment = this.document.createDocumentFragment();
                fragment.replaceChildren(container);
                const canReplace = previousSibling.querySelector(
                    "[data-embedded-editable='content'] > *:only-child"
                );
                // If the 1st block of the previous content is empty we replace it with our toggle.
                // Else we add it to the content.
                if (isEmptyBlock(canReplace)) {
                    canReplace.replaceWith(fragment);
                } else {
                    this.dependencies.dom.insert(fragment);
                }
                this.dependencies.history.addStep();
                window.setTimeout(cursors.restore, "animationFrame"); // Used to handle caret displaying issues
            }
            return true;
        }
    }

    /**
     * Handles the shift-tab behavior. This means that we need to outdent the toggle from each other.
     * @returns
     */
    handleShiftTab() {
        const selection = this.dependencies.selection.getEditableSelection();
        const closestToggleTitle = closestElement(selection.anchorNode, titleSelector);
        if (closestToggleTitle) {
            // We are indeed inside a title.
            const container = closestToggleTitle.closest("[data-embedded]");
            if (container.parentElement.closest("[data-embedded='toggle']")) {
                // If we are inside an indented toggle we need to outdent the current toggle.
                const nextPosition = rightPos(
                    container.parentElement.closest("[data-embedded='toggle']")
                );
                const cursors = this.dependencies.selection.preserveSelection();
                this.dependencies.selection.setSelection({
                    anchorNode: nextPosition[0],
                    anchorOffset: nextPosition[1],
                    focusNode: nextPosition[0],
                    focusOffset: nextPosition[1],
                });
                this.dependencies.dom.insert(container);
                cursors.restore();
                this.dependencies.history.addStep();
            }
            return true;
        }
    }

    handleSplitElementBlock({ targetNode }) {
        if (targetNode.closest("[data-embedded='toggle'] [data-embedded-editable='title']")) {
            const selection = this.dependencies.selection.getEditableSelection();
            if (isEmptyBlock(selection.anchorNode)) {
                // If no text is in title, we remove the toggle.
                const newParagraph = this.document.createElement("p");
                newParagraph.appendChild(this.document.createElement("br"));
                targetNode.closest("[data-embedded='toggle']").replaceWith(newParagraph);
                this.dependencies.selection.setCursorStart(newParagraph);
                return true;
            }
            let insertBefore;
            const container = targetNode.closest("[data-embedded='toggle']");
            const insertInside = container.firstChild.querySelector(".fa-caret-down");
            const anchorNode = selection.anchorNode.previousSibling ?? selection.anchorNode;
            if (selection.isCollapsed && selection.endOffset === 0) {
                insertBefore = selection.anchorNode.previousSibling !== null;
            }
            if (insertInside) {
                // Toggle is open
                const target = container
                    .querySelector(contentSelector)
                    .querySelector("*:first-child");
                if (insertBefore) {
                    // There is some text to move
                    const { restore } = this.dependencies.selection.preserveSelection();
                    const newParagraph = this.document.createElement("p");
                    newParagraph.replaceChildren(
                        selection.anchorNode,
                        this.document.createElement("br")
                    );
                    target.before(newParagraph); // The original anchorNode is moved in this case.
                    this.dependencies.history.addStep();
                    restore();
                } else {
                    // No text to move just change the selection
                    this.dependencies.selection.setCursorEnd(
                        target.tagName === "DIV"
                            ? target.querySelector(paragraphRelatedElements.join(","))
                            : target
                    );
                }
                return true;
            }
            const block = parseHTML(
                this.document,
                renderToString("html_editor.ToggleBlueprint", {
                    embeddedProps: JSON.stringify({ toggleId: this.getUniqueIdentifier() }),
                })
            );
            const target = block.querySelector("[data-embedded-editable='title'] > p");
            container[insertBefore ? "before" : "after"](block);
            if (selection.anchorNode.previousSibling) {
                target.replaceChildren(anchorNode, this.document.createElement("br"));
            }
            this.dependencies.history.addStep();
            if (!insertBefore) {
                this.dependencies.selection.setCursorStart(target);
            }
            return true;
        }
    }
}
