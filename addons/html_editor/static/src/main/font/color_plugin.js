import { Plugin } from "@html_editor/plugin";
import {
    isColorGradient,
    rgbaToHex,
    hasColor,
    hasAnyNodesColor,
    TEXT_CLASSES_REGEX,
    BG_CLASSES_REGEX,
    RGBA_REGEX,
} from "@html_editor/utils/color";
import { fillEmpty, unwrapContents } from "@html_editor/utils/dom";
import {
    isContentEditable,
    isEmptyBlock,
    isTextNode,
    isWhitespace,
    isZwnbsp,
} from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { isCSSColor } from "@web/core/utils/colors";
import { ColorSelector } from "./color_selector";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { withSequence } from "@html_editor/utils/resource";

const RGBA_OPACITY = 0.6;
const HEX_OPACITY = "99";

/**
 * @typedef { Object } ColorShared
 * @property { ColorPlugin['colorElement'] } colorElement
 * @property { ColorPlugin['getPropsForColorSelector'] } getPropsForColorSelector
 */
export class ColorPlugin extends Plugin {
    static id = "color";
    static dependencies = ["selection", "split", "history", "format"];
    static shared = ["colorElement", "getPropsForColorSelector"];
    resources = {
        user_commands: [
            {
                id: "applyColor",
                run: this.applyColor.bind(this),
            },
        ],
        toolbar_groups: withSequence(25, {
            id: "color",
        }),
        toolbar_items: [
            {
                id: "forecolor",
                groupId: "color",
                title: _t("Font Color"),
                Component: ColorSelector,
                props: this.getPropsForColorSelector("foreground"),
            },
            {
                id: "backcolor",
                groupId: "color",
                title: _t("Background Color"),
                Component: ColorSelector,
                props: this.getPropsForColorSelector("background"),
            },
        ],

        /** Handlers */
        selectionchange_handlers: this.updateSelectedColor.bind(this),
        remove_format_handlers: this.removeAllColor.bind(this),
    };

    setup() {
        this.selectedColors = reactive({ color: "", backgroundColor: "" });
        this.previewableApplyColor = this.dependencies.history.makePreviewableOperation(
            (color, mode, previewMode) => this._applyColor(color, mode, previewMode)
        );
    }

    /**
     * @param {'foreground'|'background'} type
     */
    getPropsForColorSelector(type) {
        const mode = type === "foreground" ? "color" : "backgroundColor";
        return {
            type,
            getUsedCustomColors: () => this.getUsedCustomColors(mode),
            getSelectedColors: () => this.selectedColors,
            applyColor: this.applyColor.bind(this),
            applyColorPreview: this.applyColorPreview.bind(this),
            applyColorResetPreview: this.applyColorResetPreview.bind(this),
            focusEditable: () => this.dependencies.selection.focusEditable(),
        };
    }

    updateSelectedColor() {
        const nodes = this.dependencies.selection.getTraversedNodes().filter(isTextNode);
        if (nodes.length === 0) {
            return;
        }
        const el = closestElement(nodes[0]);
        if (!el) {
            return;
        }
        const elStyle = getComputedStyle(el);
        const backgroundImage = elStyle.backgroundImage;
        const hasGradient = isColorGradient(backgroundImage);
        const hasTextGradientClass = el.classList.contains("text-gradient");

        let backgroundColor = elStyle.backgroundColor;
        const activeTab = document
            .querySelector(".o_font_color_selector button.active")
            ?.innerHTML.trim();
        if (backgroundColor.startsWith("rgba") && activeTab === "Solid") {
            // Buttons in the solid tab of color selector have no
            // opacity, hence to match selected color correctly,
            // we need to remove applied 0.6 opacity.
            const values = backgroundColor.match(RGBA_REGEX) || [];
            const alpha = parseFloat(values.pop()); // Extract alpha value
            if (alpha === RGBA_OPACITY) {
                backgroundColor = `rgb(${values.slice(0, 3).join(", ")})`; // Remove alpha
            }
        }

        this.selectedColors.color =
            hasGradient && hasTextGradientClass ? backgroundImage : rgbaToHex(elStyle.color);
        this.selectedColors.backgroundColor =
            hasGradient && !hasTextGradientClass ? backgroundImage : rgbaToHex(backgroundColor);
    }

    /**
     * Apply a css or class color on the current selection (wrapped in <font>).
     *
     * @param {Object} param
     * @param {string} param.color hexadecimal or bg-name/text-name class
     * @param {string} param.mode 'color' or 'backgroundColor'
     */
    applyColor({ color, mode }) {
        this.previewableApplyColor.commit(color, mode);
        this.updateSelectedColor();
    }
    /**
     * Apply a css or class color on the current selection (wrapped in <font>)
     * in preview mode so that it can be reset.
     *
     * @param {Object} param
     * @param {string} param.color hexadecimal or bg-name/text-name class
     * @param {string} param.mode 'color' or 'backgroundColor'
     */
    applyColorPreview({ color, mode }) {
        // Preview the color before applying it.
        this.previewableApplyColor.preview(color, mode, true);
        this.updateSelectedColor();
    }
    /**
     * Reset the color applied in preview mode.
     */
    applyColorResetPreview() {
        this.previewableApplyColor.revert();
        this.updateSelectedColor();
    }

    removeAllColor() {
        const colorModes = ["color", "backgroundColor"];
        let someColorWasRemoved = true;
        while (someColorWasRemoved) {
            someColorWasRemoved = false;
            for (const mode of colorModes) {
                let max = 40;
                const hasAnySelectedNodeColor = (mode) => {
                    const nodes = this.dependencies.selection
                        .getTraversedNodes()
                        .filter((n) => isTextNode(n) || n.classList.contains("o_selected_td"));
                    return hasAnyNodesColor(nodes, mode);
                };
                while (hasAnySelectedNodeColor(mode) && max > 0) {
                    this._applyColor("", mode);
                    someColorWasRemoved = true;
                    max--;
                }
                if (max === 0) {
                    someColorWasRemoved = false;
                    throw new Error("Infinite Loop in removeAllColor().");
                }
            }
        }
    }

    /**
     * Apply a css or class color on the current selection (wrapped in <font>).
     *
     * @param {string} color hexadecimal or bg-name/text-name class
     * @param {string} mode 'color' or 'backgroundColor'
     * @param {boolean} [previewMode=false] true - apply color in preview mode
     */
    _applyColor(color, mode, previewMode = false) {
        if (this.delegateTo("color_apply_overrides", color, mode, previewMode)) {
            return;
        }
        const activeTab = document
            .querySelector(".o_font_color_selector button.active")
            ?.innerHTML.trim();
        if (mode === "backgroundColor" && activeTab === "Solid" && color.startsWith("#")) {
            // Apply default transparency to selected solid tab colors in background
            // mode to make text highlighting more usable between light and dark modes.
            color += HEX_OPACITY;
        }
        let selection = this.dependencies.selection.getEditableSelection();
        let selectionNodes;
        // Get the <font> nodes to color
        if (selection.isCollapsed) {
            let zws;
            if (
                selection.anchorNode.nodeType !== Node.TEXT_NODE &&
                selection.anchorNode.textContent !== "\u200b"
            ) {
                zws = selection.anchorNode;
            } else {
                zws = this.dependencies.format.insertAndSelectZws();
            }
            selection = this.dependencies.selection.setSelection(
                {
                    anchorNode: zws,
                    anchorOffset: 0,
                },
                { normalize: false }
            );
            selectionNodes = [zws];
        } else {
            selection = this.dependencies.split.splitSelection();
            selectionNodes = this.dependencies.selection
                .getSelectedNodes()
                .filter((node) => isContentEditable(node) && node.nodeName !== "T");
            if (isEmptyBlock(selection.endContainer)) {
                selectionNodes.push(selection.endContainer, ...descendants(selection.endContainer));
            }
        }

        const selectedNodes =
            mode === "backgroundColor" && color
                ? selectionNodes.filter((node) => !closestElement(node, "table.o_selected_table"))
                : selectionNodes;

        const selectedFieldNodes = new Set(
            this.dependencies.selection
                .getSelectedNodes()
                .map((n) => closestElement(n, "*[t-field],*[t-out],*[t-esc]"))
                .filter(Boolean)
        );

        const getFonts = (selectedNodes) => {
            return selectedNodes.flatMap((node) => {
                let font = closestElement(node, "font") || closestElement(node, "span");
                const children = font && descendants(font);
                const hasInlineGradient = font && isColorGradient(font.style["background-image"]);
                if (
                    font &&
                    (font.nodeName === "FONT" || (font.nodeName === "SPAN" && font.style[mode])) &&
                    (isColorGradient(color) || color === "" || !hasInlineGradient)
                ) {
                    // Partially selected <font>: split it.
                    const selectedChildren = children.filter((child) =>
                        selectedNodes.includes(child)
                    );
                    if (selectedChildren.length) {
                        const closestGradientEl = closestElement(
                            node,
                            'font[style*="background-image"], span[style*="background-image"]'
                        );
                        const isGradientBeingUpdated = closestGradientEl && isColorGradient(color);
                        const splitnode = isGradientBeingUpdated ? closestGradientEl : font;
                        font = this.dependencies.split.splitAroundUntil(
                            selectedChildren,
                            splitnode
                        );
                        if (isGradientBeingUpdated) {
                            const classRegex =
                                mode === "color" ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX;
                            // When updating a gradient, remove color applied to
                            // its descendants.This ensures the gradient remains
                            // visible without being overwritten by a descendant's color.
                            for (const node of descendants(font)) {
                                if (
                                    node.nodeType === Node.ELEMENT_NODE &&
                                    (node.style[mode] || classRegex.test(node.className))
                                ) {
                                    this.colorElement(node, "", mode);
                                    node.style.webkitTextFillColor = "";
                                    if (!node.getAttribute("style")) {
                                        unwrapContents(node);
                                    }
                                }
                            }
                        } else if (
                            mode === "color" &&
                            (font.style.webkitTextFillColor ||
                                (closestGradientEl &&
                                    closestGradientEl.classList.contains("text-gradient")))
                        ) {
                            font.style.webkitTextFillColor = color;
                        }
                    } else {
                        font = [];
                    }
                } else if (
                    (node.nodeType === Node.TEXT_NODE && !isWhitespace(node) && !isZwnbsp(node)) ||
                    (node.nodeName === "BR" && isEmptyBlock(node.parentNode)) ||
                    (node.nodeType === Node.ELEMENT_NODE &&
                        ["inline", "inline-block"].includes(getComputedStyle(node).display) &&
                        !isWhitespace(node.textContent) &&
                        !node.classList.contains("btn") &&
                        !node.querySelector("font") &&
                        node.nodeName !== "A" &&
                        !(node.nodeName === "SPAN" && node.style["fontSize"]))
                ) {
                    // Node is a visible text or inline node without font nor a button:
                    // wrap it in a <font>.
                    const previous = node.previousSibling;
                    const classRegex = mode === "color" ? BG_CLASSES_REGEX : TEXT_CLASSES_REGEX;
                    if (
                        previous &&
                        previous.nodeName === "FONT" &&
                        !previous.style[mode === "color" ? "backgroundColor" : "color"] &&
                        !classRegex.test(previous.className) &&
                        selectedNodes.includes(previous.firstChild) &&
                        selectedNodes.includes(previous.lastChild)
                    ) {
                        // Directly follows a fully selected <font> that isn't
                        // colored in the other mode: append to that.
                        font = previous;
                    } else {
                        // No <font> found: insert a new one.
                        const isTextGradient =
                            hasInlineGradient && font.classList.contains("text-gradient");
                        font = this.document.createElement("font");
                        node.after(font);
                        if (isTextGradient && mode === "color") {
                            font.style.webkitTextFillColor = color;
                        }
                    }
                    if (node.textContent) {
                        font.appendChild(node);
                    } else {
                        fillEmpty(font);
                    }
                } else {
                    font = []; // Ignore non-text or invisible text nodes.
                }
                return font;
            });
        };

        for (const fieldNode of selectedFieldNodes) {
            this.colorElement(fieldNode, color, mode);
        }

        let fonts = getFonts(selectedNodes);
        // Dirty fix as the previous call could have unconnected elements
        // because of the `splitAroundUntil`. Another call should provide he
        // correct list of fonts.
        if (!fonts.every((font) => font.isConnected)) {
            fonts = getFonts(selectedNodes);
        }

        // Color the selected <font>s and remove uncolored fonts.
        const fontsSet = new Set(fonts);
        for (const font of fontsSet) {
            this.colorElement(font, color, mode);
            if (
                !hasColor(font, "color") &&
                !hasColor(font, "backgroundColor") &&
                (!font.hasAttribute("style") || !color)
            ) {
                for (const child of [...font.childNodes]) {
                    font.parentNode.insertBefore(child, font);
                }
                font.parentNode.removeChild(font);
                fontsSet.delete(font);
            }
        }
        this.dependencies.selection.setSelection(selection, { normalize: false });
    }

    getUsedCustomColors(mode) {
        const allFont = this.editable.querySelectorAll("font");
        const usedCustomColors = new Set();
        for (const font of allFont) {
            if (isCSSColor(font.style[mode])) {
                usedCustomColors.add(rgbaToHex(font.style[mode]));
            }
        }
        return usedCustomColors;
    }

    /**
     * Applies a css or class color (fore- or background-) to an element.
     * Replace the color that was already there if any.
     *
     * @param {Element} element
     * @param {string} color hexadecimal or bg-name/text-name class
     * @param {'color'|'backgroundColor'} mode 'color' or 'backgroundColor'
     */
    colorElement(element, color, mode) {
        const newClassName = element.className
            .replace(mode === "color" ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX, "")
            .replace(/\btext-gradient\b/g, "") // cannot be combined with setting a background
            .replace(/\s+/, " ");
        element.className !== newClassName && (element.className = newClassName);
        element.style["background-image"] = "";
        if (mode === "backgroundColor") {
            element.style["background"] = "";
        }
        if (color.startsWith("text") || color.startsWith("bg-")) {
            element.style[mode] = "";
            element.classList.add(color);
        } else if (isColorGradient(color)) {
            element.style[mode] = "";
            if (mode === "color") {
                element.style["background"] = "";
                element.style["background-image"] = color;
                element.classList.add("text-gradient");
            } else {
                element.style["background-image"] = color;
            }
        } else {
            element.style[mode] = color;
        }
    }
}
