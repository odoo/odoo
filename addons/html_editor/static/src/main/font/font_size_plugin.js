import { proxy } from "@odoo/owl";
import { Plugin } from "@html_editor/plugin";
import { removeClass, unwrapContents } from "@html_editor/utils/dom";
import { isRedundantElement } from "@html_editor/utils/dom_info";
import {
    closestElement,
    closestPath,
    descendants,
    findNode,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import {
    convertNumericToUnit,
    DEFAULT_FONT_SIZE_CLASSES,
    FONT_SIZE_CLASSES,
    getCSSVariableValue,
    getFontSizeDisplayValue,
    getHtmlStyle,
    removeStyle,
    TEXT_STYLE_CLASSES,
} from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { READ, withSequence } from "@html_editor/utils/resource";
import { FontSizeSelector, MAX_FONT_SIZE } from "./font_size_selector";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { removeFormat } from "@html_editor/core/format_plugin";

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
        user_commands: [
            {
                id: "formatFontSize",
                run: (sizeOrClass) => {
                    this.dependencies.format.requestFormat("fontSize", {
                        applyStyle: true,
                        formatProps: sizeOrClass,
                    });
                },
                isAvailable: this.dependencies.format.canFormatContent,
            },
        ],
        toolbar_items: [
            withSequence(20, {
                id: "font-size",
                commandId: "formatFontSize",
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
                            this.dependencies.format.requestFormat("fontSize", {
                                applyStyle: false,
                            });
                        } else {
                            this.dependencies.format.requestFormat("fontSize", {
                                formatProps: { size: resolvedSize },
                                applyStyle: true,
                            });
                        }
                        this.updateFontSizeSelectorParams();
                    },
                    onSelected: (item) => {
                        this.dependencies.format.requestFormat("fontSize", {
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
                    maxFontSize: this.config.maxFontSize,
                },
            }),
        ],

        /** Handlers */
        on_selectionchange_handlers: withSequence(
            READ,
            this.updateFontSizeSelectorParams.bind(this)
        ),
        on_history_commit_undone_handlers: this.updateFontSizeSelectorParams.bind(this),
        on_history_commit_redone_handlers: this.updateFontSizeSelectorParams.bind(this),
        on_will_set_tag_handlers: this.removeFontSizeFormat.bind(this),
        normalize_processors: this.normalize.bind(this),

        is_format_class_predicates: (className) => {
            if ([...FONT_SIZE_CLASSES, "o_default_font_size", "o_rfs"].includes(className)) {
                return true;
            }
        },

        format_specs: [
            {
                id: "fontSize",
                isFormatted: (node, props) => {
                    const path = [...closestPath(node)];
                    const li = closestElement(node, "li");
                    const blockParent = closestBlock(node).parentElement;
                    const stopAtBlockParent = (el) => el === blockParent;

                    const hasClass = (cls) =>
                        !!findNode(path, (el) => el.classList?.contains(cls), stopAtBlockParent) ||
                        li?.classList?.contains(cls);

                    if (props?.className) {
                        return (
                            FONT_SIZE_CLASSES.includes(props.className) && hasClass(props.className)
                        );
                    }

                    const inlineSize = (
                        findNode(path, (el) => el.style?.["font-size"], stopAtBlockParent) || li
                    )?.style["font-size"];
                    if (props?.size) {
                        return inlineSize === props.size;
                    }
                    return inlineSize || FONT_SIZE_CLASSES.some(hasClass);
                },
                hasStyle: (node) =>
                    node.style?.["font-size"] ||
                    [
                        ...FONT_SIZE_CLASSES,
                        ...TEXT_STYLE_CLASSES,
                        ...DEFAULT_FONT_SIZE_CLASSES,
                    ].find((cls) => node.classList.contains(cls)),
                addStyle: (node, props) => {
                    node.style.removeProperty("font-size");
                    removeClass(node, ...FONT_SIZE_CLASSES, "o_rfs");
                    if (props.className) {
                        node.classList.add(props.className);
                    } else {
                        node.style["font-size"] = props.size;
                        node.classList.toggle(
                            "o_rfs",
                            !!props.size && props.size.startsWith("clamp(")
                        );
                    }
                },
                removeStyle: (node) => {
                    removeStyle(node, "font-size");
                    removeClass(node, ...FONT_SIZE_CLASSES, "o_rfs", "o_default_font_size");
                    // Typography classes should be preserved on block elements since
                    // they act as semantic equivalents of <h1>, <h2>, etc., not just
                    // removable styles.
                    if (!isBlock(node)) {
                        removeClass(node, ...TEXT_STYLE_CLASSES, ...DEFAULT_FONT_SIZE_CLASSES);
                    }
                },
                addNeutralStyle: function (node) {
                    const block = closestBlock(node);
                    if (["H1", "H2", "H3", "H4", "H5", "H6"].includes(block.nodeName)) {
                        node.classList.add(block.nodeName.toLowerCase());
                    } else {
                        node.classList.add("o_default_font_size");
                    }
                },
            },
        ],
    };

    setup() {
        this.fontSize = proxy({ displayName: "" });
        this.isTypingFontSize = false;
    }

    normalize(root) {
        for (const el of selectElements(root, "small")) {
            if (isRedundantElement(el)) {
                unwrapContents(el);
            }
        }
        return root;
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
     *      `clamp(8px, 1em + UIvalue*vw, this.config.maxFontSize || MAX_FONT_SIZE)`
     *  - For frontend: `maxFontSize` comes from config (400), with fallback to
     *    backend default MAX_FONT_SIZE (144)
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
        return `clamp(8px, 1em + ${uiValue.toFixed(4)}vw, ${
            this.config.maxFontSize || MAX_FONT_SIZE
        }px)`;
    }

    updateFontSizeSelectorParams() {
        if (this.isTypingFontSize) {
            return;
        }
        this.fontSize.displayName = this.fontSizeName;
    }

    removeFontSizeFormat({ block }) {
        const fontSizeSpec = this.getResource("format_specs").find(
            (spec) => spec.id === "fontSize"
        );
        for (const node of [block, ...descendants(block)]) {
            removeFormat(node, fontSizeSpec);
        }
    }
}
