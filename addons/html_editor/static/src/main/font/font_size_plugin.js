import { reactive } from "@web/owl2/utils";
import { Plugin } from "@html_editor/plugin";
import { unwrapContents } from "@html_editor/utils/dom";
import { isRedundantElement, isStylable } from "@html_editor/utils/dom_info";
import { selectElements } from "@html_editor/utils/dom_traversal";
import {
    convertNumericToUnit,
    getCSSVariableValue,
    getHtmlStyle,
    getFontSizeDisplayValue,
    FONT_SIZE_CLASSES,
} from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { READ, withSequence } from "@html_editor/utils/resource";
import { FontSizeSelector, MAX_FONT_SIZE } from "./font_size_selector";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { closestBlock } from "@html_editor/utils/blocks";

/** @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString */

export const fontSizeItems = [
    { variableName: "display-1-font-size", className: "display-1-fs" },
    { variableName: "display-2-font-size", className: "display-2-fs" },
    { variableName: "display-3-font-size", className: "display-3-fs" },
    { variableName: "display-4-font-size", className: "display-4-fs" },
    { variableName: "h1-font-size", className: "h1-fs" },
    { variableName: "h2-font-size", className: "h2-fs" },
    { variableName: "h3-font-size", className: "h3-fs" },
    { variableName: "h4-font-size", className: "h4-fs" },
    { variableName: "h5-font-size", className: "h5-fs" },
    { variableName: "h6-font-size", className: "h6-fs" },
    { variableName: "font-size-base", className: "base-fs" },
    { variableName: "small-font-size", className: "o_small-fs" },
];

export class FontSizePlugin extends Plugin {
    static id = "fontSize";
    static dependencies = ["format", "selection"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        toolbar_items: [
            withSequence(20, {
                id: "font-size",
                groupId: "font",
                namespaces: ["compact", "expanded"],
                description: _t("Select font size"),
                Component: FontSizeSelector,
                props: {
                    getItems: () => this.fontSizeItems,
                    getDisplay: () => this.fontSize,
                    onFontSizeInput: (size) => {
                        this.isTypingFontSize = true;
                        const resolvedSize = this.resolveFontSize(parseFloat(size));
                        if (resolvedSize === null) {
                            // Desired size matches the inherited value
                            this.dependencies.format.formatSelection("fontSize", {
                                applyStyle: false,
                            });
                        } else {
                            this.dependencies.format.formatSelection("fontSize", {
                                formatProps: { size: resolvedSize },
                                applyStyle: true,
                            });
                        }
                        this.updateFontSizeSelectorParams();
                    },
                    onSelected: (item) => {
                        this.dependencies.format.formatSelection("setFontSizeClassName", {
                            formatProps: { className: item.className },
                            applyStyle: true,
                        });
                        this.updateFontSizeSelectorParams();
                    },
                    onBlur: () => {
                        this.isTypingFontSize = false;
                        this.updateFontSizeSelectorParams();
                        this.dependencies.selection.focusEditable();
                    },
                    document: this.document,
                },
                isAvailable: isHtmlContentSupported,
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
            }),
        ],

        /** Handlers */
        on_selectionchange_handlers: withSequence(
            READ,
            this.updateFontSizeSelectorParams.bind(this)
        ),
        on_undone_handlers: this.updateFontSizeSelectorParams.bind(this),
        on_redone_handlers: this.updateFontSizeSelectorParams.bind(this),
        normalize_processors: this.normalize.bind(this),

        is_format_class_predicates: (className) => {
            if ([...FONT_SIZE_CLASSES, "o_default_font_size", "o_rfs"].includes(className)) {
                return true;
            }
        },
    };

    setup() {
        this.fontSize = reactive({ displayName: "" });
        this.isTypingFontSize = false;
    }

    normalize(root) {
        for (const el of selectElements(root, "small")) {
            if (isRedundantElement(el)) {
                unwrapContents(el);
            }
        }
    }

    get fontSizeName() {
        const sel = this.dependencies.selection.getSelectionData().deepEditableSelection;
        if (!sel) {
            return fontSizeItems[0].name;
        }
        return Math.round(getFontSizeDisplayValue(sel, this.document));
    }

    get fontSizeItems() {
        const style = getHtmlStyle(this.document);
        const nameAlreadyUsed = new Set();
        return fontSizeItems
            .flatMap((item) => {
                const strValue = getCSSVariableValue(item.variableName, style);
                if (!strValue) {
                    return [];
                }
                const remValue = parseFloat(strValue);
                const pxValue = convertNumericToUnit(remValue, "rem", "px", style);
                const roundedValue = Math.round(pxValue);
                if (nameAlreadyUsed.has(roundedValue)) {
                    return [];
                }
                nameAlreadyUsed.add(roundedValue);

                return [{ ...item, tagName: "span", name: roundedValue }];
            })
            .sort((a, b) => a.name - b.name);
    }

    /**
     * Resolves the CSS font-size value to apply for a desired pixel size typed
     * by the user in the toolbar input.
     *
     * Strategy:
     *  - If the value falls within the range of system-defined font sizes,
     *    a plain `px` value is returned, those sizes are already designed by
     *    the user to work at any viewport.
     *  - If the value is outside that range (smaller than the smallest system
     *    size, or larger than the largest), a responsive `clamp()` expression
     *    is returned so the text scales gracefully with the viewport:
     *      `clamp(8px, 1em + UIvalue*vw, MAX_FONT_SIZE)`
     *    where `UIvalue` is derived from the difference between what the user
     *    wants and what the parent block already provides at the current viewport.
     *
     * Returns `null` when the desired size matches the inherited size (within a
     * 0.01 vw tolerance), signalling that any existing inline override should
     * simply be removed.
     *
     * @param {number} desiredPx  The pixel value the user typed in the toolbar.
     * @returns {string|null}     A CSS font-size value, or `null`.
     */
    resolveFontSize(desiredPx) {
        const items = this.fontSizeItems;
        if (items.length) {
            const minPx = items[0].name;
            const maxPx = items[items.length - 1].name;
            if (desiredPx >= minPx && desiredPx <= maxPx) {
                // Within the system-defined range: plain px is fine.
                return `${desiredPx}px`;
            }
        }
        // Outside the system range => produce responsive value.
        const sel = this.dependencies.selection.getEditableSelection();
        const blockEl = closestBlock(sel.anchorNode);
        const parentComputedPx = parseFloat(this.window.getComputedStyle(blockEl).fontSize);
        const viewportWidth = this.window.innerWidth;
        const uiValue = (desiredPx - parentComputedPx) / (viewportWidth / 100);
        if (Math.abs(uiValue) < 0.01) {
            // Desired size matches the inherited size — clear any existing
            // existing inline override.
            return null;
        }
        return `clamp(8px, 1em + ${uiValue.toFixed(4)}vw, ${MAX_FONT_SIZE}px)`;
    }

    updateFontSizeSelectorParams() {
        if (this.isTypingFontSize) {
            return;
        }
        this.fontSize.displayName = this.fontSizeName;
    }
}
