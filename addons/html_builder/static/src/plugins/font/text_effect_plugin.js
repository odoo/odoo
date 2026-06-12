import { proxy } from "@odoo/owl";
import { Plugin } from "@html_editor/plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { childNodeIndex, DIRECTIONS, nodeSize } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { TextEffectSelector } from "./text_effect_selector";
import { BuilderAction } from "@html_builder/core/builder_action";
import {
    applyConfiguredEffects,
    defaults,
    deleteShadowParam,
    getActualColor,
    getShadowCount,
    getShadows,
    getTextEffectPresetId,
    hasConfiguredTextEffect,
    isShadowParam,
    setShadowParam,
    updateTextEffectPresetHash,
} from "./text_effect_util";
import {
    ancestors,
    closestElement,
    descendants,
    findFurthest,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { getDeepestEditablePosition, isTextNode } from "@html_editor/utils/dom_info";

export class TextEffectPlugin extends Plugin {
    static id = "textEffect";
    static dependencies = ["selection", "split", "history", "format"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        builder_actions: {
            UpdateTextEffectAction,
        },
        toolbar_items: [
            withSequence(15, {
                id: "textEffect",
                groupId: "decoration",
                namespaces: ["expanded"],
                description: _t("Apply Text Effects"),
                Component: TextEffectSelector,
                props: {
                    config: this.config.getAnimateTextConfig(), // TODO obtain a more neutral method name
                    prepareTextEffectSelection: this.prepareTextEffectSelection.bind(this),
                    applyTextEffect: this.applyTextEffect.bind(this),
                    previewTextEffect: this.previewTextEffect.bind(this),
                    revertTextEffect: this.revertTextEffect.bind(this),
                    getState: () => this.toolbarIconState,
                    updateState: () => {
                        this.toolbarIconState.isActive = this.isTextEffectActive();
                        this.toolbarIconState.isDisabled = this.isTextEffectDisabled();
                    },
                },
                isAvailable: (selection) =>
                    isHtmlContentSupported(selection) && !selection.isCollapsed,
            }),
        ],
        can_remove_format_predicates: (editableTargetedNodes) => {
            if (
                editableTargetedNodes.some((node) => {
                    const effectEl = closestElement(node, "[data-text-effect]");
                    return effectEl && JSON.parse(effectEl.dataset.textEffect).preset;
                })
            ) {
                return true;
            }
        },
        is_node_splittable_predicates: (node) => {
            if (node.matches?.("[data-text-effect]")) {
                return false;
            }
        },
        clean_for_save_processors: this.removeEmptyTextEffects.bind(this),
        on_all_formats_removed_handlers: () => {
            for (const node of this.dependencies.selection.getTargetedNodes()) {
                const formattedElement = closestElement(node, "[data-text-effect]");
                if (formattedElement) {
                    delete formattedElement.dataset.textEffect;
                    applyConfiguredEffects(formattedElement);
                    this.toolbarIconState.isActive = this.isTextEffectActive();
                    this.toolbarIconState.isDisabled = this.isTextEffectDisabled();
                }
            }
        },
    };
    setup() {
        this.previewableApplyTextEffect = this.dependencies.history.makePreviewableOperation(
            this._applyTextEffect.bind(this)
        );
        this.toolbarIconState = proxy({
            isActive: undefined,
            isDisabled: undefined,
        });
    }
    /**
     * Returns the element that is a text with an effect that corresponds to the
     * current selection (if there is any)
     *
     * @returns {HTMLElement?}
     */
    getTextEffect() {
        const selection = this.dependencies.selection.getSelectionData().editableSelection;
        const ancestor = closestElement(selection.commonAncestorContainer, "[data-text-effect]");
        if (ancestor) {
            const selectionText = selection.toString().replace(/\s+/g, " ").trim();
            const ancestorText = ancestor.innerText.replace(/\s+/g, " ").trim();
            if (selection.isCollapsed || selectionText === ancestorText) {
                return ancestor;
            }
        } else if (selection.commonAncestorContainer.nodeType === Node.ELEMENT_NODE) {
            // Find first nested text effect
            return selectElements(selection.commonAncestorContainer, "[data-text-effect]")[0];
        }
    }
    getSelectedTextEffects() {
        const selection = this.dependencies.selection.getSelectionData().editableSelection;
        const commonAncestor =
            selection.commonAncestorContainer.nodeType === Node.ELEMENT_NODE
                ? selection.commonAncestorContainer
                : selection.commonAncestorContainer.parentElement;
        const textEffects = [
            closestElement(selection.startContainer, "[data-text-effect]"),
            closestElement(selection.endContainer, "[data-text-effect]"),
            ...selectElements(commonAncestor || this.editable, "[data-text-effect]").filter((el) =>
                selection.intersectsNode(el)
            ),
        ].filter(Boolean);
        return [...new Set(textEffects)].sort((a, b) =>
            a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_PRECEDING ? 1 : -1
        );
    }
    isSelectionWithinTextEffect(textEffect) {
        const selection = this.dependencies.selection.getSelectionData().editableSelection;
        return (
            textEffect.contains(selection.startContainer) &&
            textEffect.contains(selection.endContainer)
        );
    }
    completeTextEffectSelection() {
        const selection = this.dependencies.selection.getEditableSelection();
        let { startContainer, startOffset, endContainer, endOffset, direction } = selection;
        const originalSelection = { startContainer, startOffset, endContainer, endOffset };
        const startTextEffect = closestElement(startContainer, "[data-text-effect]");
        const endTextEffect = closestElement(endContainer, "[data-text-effect]");

        if (startTextEffect) {
            const firstTextNode = descendants(startTextEffect).find(isTextNode);
            if (firstTextNode) {
                startContainer = firstTextNode;
                startOffset = 0;
            }
        }
        if (endTextEffect) {
            const lastTextNode = descendants(endTextEffect).filter(isTextNode).at(-1);
            if (lastTextNode) {
                endContainer = lastTextNode;
                endOffset = nodeSize(endContainer);
            }
        }
        const didExpandSelection = !(
            startContainer === originalSelection.startContainer &&
            startOffset === originalSelection.startOffset &&
            endContainer === originalSelection.endContainer &&
            endOffset === originalSelection.endOffset
        );
        if (!didExpandSelection) {
            return false;
        }
        const [anchorNode, anchorOffset, focusNode, focusOffset] =
            direction === DIRECTIONS.RIGHT
                ? [startContainer, startOffset, endContainer, endOffset]
                : [endContainer, endOffset, startContainer, startOffset];
        this.dependencies.selection.setSelection({
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        });
        this.dependencies.selection.focusEditable();
        this.dependencies.selection.stageSelection();
        return true;
    }
    getTextEffectState() {
        const selectedTextEffects = this.getSelectedTextEffects();
        const element =
            selectedTextEffects.length === 1 &&
            this.isSelectionWithinTextEffect(selectedTextEffects[0])
                ? selectedTextEffects[0]
                : undefined;
        return {
            element,
            hasTextEffect: selectedTextEffects.length > 0,
            activePreset: element
                ? getTextEffectPresetId(JSON.parse(element.dataset.textEffect || "{}"))
                : undefined,
        };
    }
    prepareTextEffectSelection() {
        this.completeTextEffectSelection();
        return this.getTextEffectState();
    }
    applyTextEffect(effectJson) {
        this.previewableApplyTextEffect.commit(effectJson);
        return this.getTextEffectState();
    }
    previewTextEffect(effectJson) {
        this.previewableApplyTextEffect.preview(effectJson);
    }
    revertTextEffect() {
        this.previewableApplyTextEffect.revert();
    }
    setTextEffect(element, effect, previousTextEffect = {}) {
        if (Object.keys(effect).length) {
            updateTextEffectPresetHash(effect);
            element.dataset.textEffect = JSON.stringify(effect);
        } else {
            delete element.dataset.textEffect;
        }
        applyConfiguredEffects(element, previousTextEffect);
        if (element.dataset.textEffect) {
            const textEffect = JSON.parse(element.dataset.textEffect);
            updateTextEffectPresetHash(textEffect);
            element.dataset.textEffect = JSON.stringify(textEffect);
        }
    }
    _applyTextEffect(effectJson) {
        const effect = JSON.parse(effectJson);
        const selectedTextEffects = this.getSelectedTextEffects();
        if (!Object.keys(effect).length) {
            const cursors = this.dependencies.selection.preserveSelection();
            for (const textEffect of selectedTextEffects) {
                unwrapContents(textEffect);
            }
            cursors.restore();
            return;
        }

        if (
            selectedTextEffects.length === 1 &&
            this.isSelectionWithinTextEffect(selectedTextEffects[0])
        ) {
            const previousTextEffect = JSON.parse(
                selectedTextEffects[0].dataset.textEffect || "{}"
            );
            this.setTextEffect(selectedTextEffects[0], effect, previousTextEffect);
            return;
        }

        const { element } = this.createDefaultTextEffect();
        if (element) {
            this.setTextEffect(element, effect);
        }
    }
    /**
     * @return {HTMLElement?} The `commonAncestorContainer` after the split
     * (null if splits are prevented by an unsplittable node)
     */
    splitForTextEffect({ anchorNode, focusNode, commonAncestorContainer }) {
        let commonAncestor = commonAncestorContainer;
        for (let [node, forward] of [
            [anchorNode, true],
            [focusNode, false],
        ]) {
            let needToMeetCommonAncestor =
                node !== commonAncestor && node.parentNode !== commonAncestor;
            let needToMeetTextEffectAncestor = !!closestElement(node, "[data-text-effect]");
            let updatedCommonAncestor = needToMeetCommonAncestor ? undefined : commonAncestor;

            // Go up to the common ancestor of the selection, or to the
            // containing text with effect (whichever is the furthest)
            while (needToMeetCommonAncestor || needToMeetTextEffectAncestor) {
                if (needToMeetTextEffectAncestor && node.parentNode.matches("[data-text-effect]")) {
                    needToMeetTextEffectAncestor = false;
                }
                const updatingCommonAncestor = commonAncestor === node.parentNode;
                const splitIndex = childNodeIndex(node);
                if (forward ? splitIndex > 0 : splitIndex < node.parentNode.childNodes.length - 1) {
                    // Split the node if needed, abort if unsplittable (unless it is a text with effect)
                    if (
                        this.dependencies.split.isUnsplittable(node.parentNode) &&
                        !node.parentNode.matches("[data-text-effect]")
                    ) {
                        return;
                    }
                    node = this.dependencies.split.splitElement(
                        node.parentNode,
                        splitIndex + (forward ? 0 : 1)
                    )[forward ? 1 : 0];
                } else {
                    node = node.parentNode;
                }
                if (updatingCommonAncestor) {
                    updatedCommonAncestor = node.parentNode;
                }
                if (needToMeetCommonAncestor && node.parentNode === commonAncestor) {
                    needToMeetCommonAncestor = false;
                }
            }
            commonAncestor = updatedCommonAncestor || commonAncestor;
        }
        return commonAncestor;
    }
    /**
     * Create a span with the default text effect, on the selection
     *
     * @returns {{element: HTMLElement, didRemoveOtherTextEffect: boolean}|{}}
     */
    createDefaultTextEffect() {
        /*
        We need to create 1 element with the content of the selection to set the
        text effect. This element must be the only text effect element for
        the selected text

        To be able to create 1 new element containing the selection, we need to
        split the elements that are descendants of the common ancestor and that
        contains one end of the selection.

        To remove any other overlapping effect on text, we need to:
        - remove the effect on the part of a splitted element that falls
          inside the selection
        - split ancestor text with effect that fully contains the selection, to
          remove the effect on the part containing the selection
        - remove text effect inside of the created element

        If these splits would split an unsplittable node, we abort
        */
        this.dependencies.split.splitSelection();
        const selection = this.dependencies.selection.getSelectionData().deepEditableSelection;
        this.dependencies.selection.setSelection(selection);
        const commonAncestor = this.splitForTextEffect(selection);
        if (!commonAncestor) {
            return {};
        }
        const { startContainer, endContainer, direction } = selection;

        const range = new Range();
        range.setStartBefore(
            findFurthest(startContainer, commonAncestor, () => true) || startContainer
        );
        range.setEndAfter(findFurthest(endContainer, commonAncestor, () => true) || endContainer);
        const span = this.document.createElement("span");
        range.surroundContents(span);
        // Remove text effect inside the span and containing the span (the ancestors have been split so it only contains the span)
        let didRemoveOtherTextEffect = false;
        for (const node of [
            ...span.querySelectorAll("[data-text-effect]"),
            ...ancestors(span, this.editable).filter((n) => n.matches("[data-text-effect]")),
        ]) {
            unwrapContents(node);
            didRemoveOtherTextEffect = true;
        }
        const recycleFromElement =
            closestElement(span.previousSibling || span, "[data-text-effect]") ||
            closestElement(span.nextSibling || span, "[data-text-effect]");
        if (recycleFromElement) {
            // Start from neighbour's effects.
            span.dataset.textEffect = recycleFromElement.dataset.textEffect;
        } else {
            // Start from defaults.
            span.dataset.textEffect = JSON.stringify({});
        }
        applyConfiguredEffects(span);
        // Select the deepest editable positions instead of the text-effect wrapper itself.
        // The wrapper can contain block elements (<p>, headings, etc.), and later formatting
        // operations (like font size) may introduce nested inline spans inside those blocks.
        // Keeping the selection on the wrapper boundaries causes selection restoration issues
        // when the text-effect wrapper is removed/unwrapped.
        const [selectionStart, selectionEnd] = [
            getDeepestEditablePosition(span, 0),
            getDeepestEditablePosition(span, nodeSize(span)),
        ];
        this.dependencies.selection.setSelection(
            direction === DIRECTIONS.RIGHT
                ? {
                      anchorNode: selectionStart[0],
                      anchorOffset: selectionStart[1],
                      focusNode: selectionEnd[0],
                      focusOffset: selectionEnd[1],
                  }
                : {
                      anchorNode: selectionEnd[0],
                      anchorOffset: selectionEnd[1],
                      focusNode: selectionStart[0],
                      focusOffset: selectionStart[1],
                  }
        );
        return { element: span, didRemoveOtherTextEffect };
    }
    isTextEffectActive() {
        const textEffectEl = this.getTextEffect();
        if (!textEffectEl) {
            return false;
        }
        return !!Object.keys(JSON.parse(textEffectEl.dataset.textEffect || "{}")).length;
    }
    isTextEffectDisabled() {
        return 2 <= this.dependencies.selection.getTargetedNodes().size;
    }
    removeEmptyTextEffects(root) {
        for (const el of selectElements(root, "[data-text-effect]")) {
            const textEffect = JSON.parse(el.dataset.textEffect || "{}");
            if (!hasConfiguredTextEffect(textEffect)) {
                unwrapContents(el);
            }
        }
        return root;
    }
}

export class UpdateTextEffectAction extends BuilderAction {
    static id = "updateTextEffect";
    static emptyShadow = {
        shadowColor: "transparent",
        shadowOffsetX: "0px",
        shadowOffsetY: "0px",
        shadowBlur: "0px",
    };

    getValue({ editingElement, params: { mainParam: variable, shadowIndex = 0 } }) {
        const json = JSON.parse(editingElement.dataset.textEffect || "{}");
        let value;
        if (isShadowParam(variable)) {
            const hasShadow = !!getShadowCount(json);
            value = hasShadow
                ? getShadows(json)[shadowIndex]?.[variable] ?? defaults[variable]
                : UpdateTextEffectAction.emptyShadow[variable];
        } else {
            value = json[variable] ?? defaults[variable];
        }
        if (variable.toLowerCase().endsWith("color")) {
            value = getActualColor(value, this.document);
        }
        return value;
    }
    isApplied({ editingElement, params, value }) {
        return this.getValue({ editingElement, params }) === value;
    }
    apply({ editingElement, params: { mainParam: variable, shadowIndex = 0 }, value }) {
        const json = JSON.parse(editingElement.dataset.textEffect || "{}");
        if (isShadowParam(variable)) {
            const hasShadow = !!getShadowCount(json);
            const defaultValue = hasShadow
                ? defaults[variable]
                : UpdateTextEffectAction.emptyShadow[variable];
            if (value && value !== defaultValue) {
                if (!hasShadow) {
                    json.shadows = [];
                    while (json.shadows.length <= shadowIndex) {
                        json.shadows.push({ ...UpdateTextEffectAction.emptyShadow });
                    }
                }
                setShadowParam(json, variable, shadowIndex, value);
            } else if (hasShadow) {
                deleteShadowParam(json, variable, shadowIndex);
            } else {
                return;
            }
        } else if (value && value !== defaults[variable]) {
            json[variable] = value;
        } else {
            delete json[variable];
        }
        updateTextEffectPresetHash(json);
        editingElement.dataset.textEffect = JSON.stringify(json);
        applyConfiguredEffects(editingElement);
    }
}
