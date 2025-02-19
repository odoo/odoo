import { Plugin } from "@html_editor/plugin";
import {
    BG_CLASSES_REGEX,
    COLOR_COMBINATION_CLASSES_REGEX,
    hasAnyNodesColor,
    hasColor,
    TEXT_CLASSES_REGEX,
} from "@html_editor/utils/color";
import { fillEmpty, unwrapContents } from "@html_editor/utils/dom";
import {
    isContentEditable,
    isEmptyBlock,
    isRedundantElement,
    isTextNode,
    isWhitespace,
    isZwnbsp,
} from "@html_editor/utils/dom_info";
import { closestElement, descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { isColorGradient, isCSSColor, RGBA_REGEX, rgbaToHex } from "@web/core/utils/colors";
import { ColorSelector } from "./color_selector";
import { backgroundImageCssToParts, backgroundImagePartsToCss } from "@html_editor/utils/image";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { isBlock } from "@html_editor/utils/blocks";

const RGBA_OPACITY = 0.6;
const HEX_OPACITY = "99";
const COLOR_COMBINATION_CLASSES = [1, 2, 3, 4, 5].map((i) => `o_cc${i}`);
const COLOR_COMBINATION_SELECTOR = COLOR_COMBINATION_CLASSES.map((c) => `.${c}`).join(", ");

/**
 * @typedef { Object } ColorShared
 * @property { ColorPlugin['colorElement'] } colorElement
 * @property { ColorPlugin['getPropsForColorSelector'] } getPropsForColorSelector
 */
export class ColorPlugin extends Plugin {
    static id = "color";
    static dependencies = ["selection", "split", "history", "format"];
    static shared = [
        "colorElement",
        "getPropsForColorSelector",
        "removeAllColor",
        "getElementColors",
        "getColorCombination",
    ];
    resources = {
        user_commands: [
            {
                id: "applyColor",
                run: this.applyColor.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        toolbar_items: [
            {
                id: "forecolor",
                groupId: "decoration",
                description: _t("Apply Font Color"),
                Component: ColorSelector,
                props: this.getPropsForColorSelector("foreground"),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "backcolor",
                groupId: "decoration",
                description: _t("Apply Background Color"),
                Component: ColorSelector,
                props: this.getPropsForColorSelector("background"),
                isAvailable: isHtmlContentSupported,
            },
        ],

        /** Handlers */
        selectionchange_handlers: this.updateSelectedColor.bind(this),
        remove_format_handlers: this.removeAllColor.bind(this),
        color_combination_getters: getColorCombinationFromClass,

        /** Overridables */
        /**
         * Makes the way colors are applied overridable.
         *
         * @param {Element} element
         * @param {string} color hexadecimal or bg-name/text-name class
         * @param {'color'|'backgroundColor'} mode 'color' or 'backgroundColor'
         */
        apply_style: (element, mode, color) => {
            element.style[mode] = color;
            return true;
        },

        /** Predicates */
        has_format_predicates: [
            (node) => hasColor(closestElement(node), "color"),
            (node) => hasColor(closestElement(node), "backgroundColor"),
        ],
        format_class_predicates: (className) =>
            TEXT_CLASSES_REGEX.test(className) || BG_CLASSES_REGEX.test(className),
        normalize_handlers: this.normalize.bind(this),
    };

    setup() {
        this.selectedColors = reactive({ color: "", backgroundColor: "" });
        this.previewableApplyColor = this.dependencies.history.makePreviewableOperation(
            (color, mode, previewMode) => this._applyColor(color, mode, previewMode)
        );
    }

    normalize(root) {
        for (const el of selectElements(root, "font")) {
            if (isRedundantElement(el)) {
                unwrapContents(el);
            }
        }
    }

    /**
     * @param {'foreground'|'background'} type
     */
    getPropsForColorSelector(type) {
        const mode = type === "foreground" ? "color" : "backgroundColor";
        return {
            type,
            mode,

            getUsedCustomColors: () => this.getUsedCustomColors(mode),
            getSelectedColors: () => this.selectedColors,
            applyColor: (color) => {
                this.applyColor({ color, mode });
            },
            applyColorPreview: (color) => this.applyColorPreview({ color, mode }),
            applyColorResetPreview: this.applyColorResetPreview.bind(this),
            colorPrefix: mode === "color" ? "text-" : "bg-",
            onClose: () => this.dependencies.selection.focusEditable(),
        };
    }

    updateSelectedColor() {
        const nodes = this.dependencies.selection.getTargetedNodes().filter(isTextNode);
        if (nodes.length === 0) {
            return;
        }
        const el = closestElement(nodes[0]);
        if (!el) {
            return;
        }

        Object.assign(this.selectedColors, this.getElementColors(el));
    }

    getElementColors(el) {
        const elStyle = getComputedStyle(el);
        const backgroundImage = elStyle.backgroundImage;
        const gradient = backgroundImageCssToParts(backgroundImage).gradient;
        const hasGradient = isColorGradient(gradient);
        const hasTextGradientClass = el.classList.contains("text-gradient");

        let backgroundColor = elStyle.backgroundColor;
        const activeTab = document
            .querySelector(".o_font_color_selector button.active")
            ?.innerHTML.trim();
        if (backgroundColor.startsWith("rgba") && (!activeTab || activeTab === "Solid")) {
            // Buttons in the solid tab of color selector have no
            // opacity, hence to match selected color correctly,
            // we need to remove applied 0.6 opacity.
            const values = backgroundColor.match(RGBA_REGEX) || [];
            const alpha = parseFloat(values.pop()); // Extract alpha value
            if (alpha === RGBA_OPACITY) {
                backgroundColor = `rgb(${values.slice(0, 3).join(", ")})`; // Remove alpha
            }
        }

        return {
            color: hasGradient && hasTextGradientClass ? gradient : rgbaToHex(elStyle.color),
            backgroundColor:
                hasGradient && !hasTextGradientClass ? gradient : rgbaToHex(backgroundColor),
        };
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
                        .getTargetedNodes()
                        .filter(
                            (n) =>
                                isTextNode(n) ||
                                (mode === "backgroundColor" &&
                                    n.classList.contains("o_selected_td"))
                        );
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
        this.dependencies.selection.selectAroundNonEditable();
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
        let targetedNodes;
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
            targetedNodes = [zws];
        } else {
            selection = this.dependencies.split.splitSelection();
            targetedNodes = this.dependencies.selection
                .getTargetedNodes()
                .filter((node) => isContentEditable(node) && node.nodeName !== "T");
            if (isEmptyBlock(selection.endContainer)) {
                targetedNodes.push(selection.endContainer, ...descendants(selection.endContainer));
            }
        }

        const findTopMostDecoration = (current) => {
            const decoration = closestElement(current.parentNode, "s, u");
            return decoration?.textContent === current.textContent
                ? findTopMostDecoration(decoration)
                : current;
        };

        const hexColor = rgbaToHex(color).toLowerCase();
        const selectedNodes = targetedNodes
            .filter((node) => {
                if (mode === "backgroundColor" && color) {
                    return !closestElement(node, "table.o_selected_table");
                }
                const li = closestElement(node, "li");
                if (li && color && this.dependencies.selection.areNodeContentsFullySelected(li)) {
                    return rgbaToHex(li.style.color).toLowerCase() !== hexColor;
                }
                return true;
            })
            .map((node) => findTopMostDecoration(node));

        const targetedFieldNodes = new Set(
            this.dependencies.selection
                .getTargetedNodes()
                .map((n) => closestElement(n, "*[t-field],*[t-out],*[t-esc]"))
                .filter(Boolean)
        );

        const getFonts = (selectedNodes) =>
            selectedNodes.flatMap((node) => {
                let font =
                    closestElement(node, "font") ||
                    closestElement(
                        node,
                        '[style*="color"]:not(li), [style*="background-color"]:not(li), [style*="background-image"]:not(li)'
                    ) ||
                    closestElement(node, "span");
                const children = font && descendants(font);
                const hasInlineGradient = font && isColorGradient(font.style["background-image"]);
                if (
                    font &&
                    font.nodeName !== "T" &&
                    (font.nodeName !== "SPAN" || font.style[mode] || font.style.backgroundImage) &&
                    (isColorGradient(color) || color === "" || !hasInlineGradient) &&
                    !this.dependencies.split.isUnsplittable(font)
                ) {
                    // Partially selected <font>: split it.
                    const selectedChildren = children.filter((child) =>
                        selectedNodes.includes(child)
                    );
                    if (selectedChildren.length) {
                        if (isBlock(font)) {
                            const colorStyles = ["color", "background-color", "background-image"];
                            const newFont = this.document.createElement("font");
                            for (const style of colorStyles) {
                                const styleValue = font.style[style];
                                if (styleValue) {
                                    this.colorElement(newFont, styleValue, style);
                                    font.style.removeProperty(style);
                                }
                            }
                            newFont.append(...font.childNodes);
                            font.append(newFont);
                            font = newFont;
                        }
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

        for (const fieldNode of targetedFieldNodes) {
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
            const closestLI = closestElement(font, "li");
            if (font && color === "" && closestLI?.style.color) {
                color = "initial";
            }
            this.colorElement(font, color, mode);
            if (
                !hasColor(font, "color") &&
                !hasColor(font, "backgroundColor") &&
                ["FONT", "SPAN"].includes(font.nodeName) &&
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
        let parts = backgroundImageCssToParts(element.style["background-image"]);
        const oldClassName = element.getAttribute("class") || "";

        if (element.matches(COLOR_COMBINATION_SELECTOR)) {
            removePresetGradient(element);
        }

        if (color.startsWith("o_cc")) {
            parts = backgroundImageCssToParts(element.style["background-image"]);
            element.classList.remove(...COLOR_COMBINATION_CLASSES);
            element.classList.add("o_cc", color);

            const hasBackgroundColor = !!getComputedStyle(element).backgroundColor;
            const hasGradient = getComputedStyle(element).backgroundImage.includes("-gradient");
            const backgroundImage = element.style["background-image"];
            // Override gradient background image if coming from css rather than inline style.
            if (hasBackgroundColor && hasGradient && !backgroundImage) {
                element.style.backgroundImage = "none";
            }
            this.fixColorCombination(element, color);
            return;
        }

        if (mode === "backgroundColor") {
            if (!color) {
                element.classList.remove("o_cc", ...COLOR_COMBINATION_CLASSES);
            }
            const hasGradient = getComputedStyle(element).backgroundImage.includes("-gradient");
            delete parts.gradient;
            let newBackgroundImage = backgroundImagePartsToCss(parts);
            // we override the bg image if the new bg image is empty, but the previous one is a gradient.
            if (hasGradient && !newBackgroundImage) {
                newBackgroundImage = "none";
            }
            element.style.backgroundImage = newBackgroundImage;
            element.style["background-color"] = "";
        }

        const newClassName = oldClassName
            .replace(mode === "color" ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX, "")
            .replace(/\btext-gradient\b/g, "") // cannot be combined with setting a background
            .replace(/\s+/, " ");
        if (oldClassName !== newClassName) {
            element.setAttribute("class", newClassName);
        }
        if (color.startsWith("text") || color.startsWith("bg-")) {
            element.style[mode] = "";
            element.classList.add(color);
        } else if (isColorGradient(color)) {
            element.style[mode] = "";
            parts.gradient = color;
            if (mode === "color") {
                element.style["background-color"] = "";
                element.classList.add("text-gradient");
            }
            this.delegateTo(
                "apply_style",
                element,
                "background-image",
                backgroundImagePartsToCss(parts)
            );
        } else {
            // Change camelCase to kebab-case.
            mode = mode.replace("backgroundColor", "background-color");
            this.delegateTo("apply_style", element, mode, color);
        }
        this.fixColorCombination(element, color);
    }
    /**
     * There is a limitation with css. The defining a background image and a
     * background gradient is done only by setting one style (background-image).
     * If there is a class (in this case o_cc[1-5]) that defines a gradient, it
     * will be overridden by the background-image property.
     *
     * This function will set the gradient of the o_cc in the background-image
     * so that setting an image in the background-image property will not
     * override the gradient.
     */
    fixColorCombination(element, color) {
        const parts = backgroundImageCssToParts(element.style["background-image"]);
        const hasBackgroundColor =
            element.style["background-color"] ||
            !!element.className.match(/\bbg-/) ||
            parts.gradient;

        if (!hasBackgroundColor && (isColorGradient(color) || color.startsWith("o_cc"))) {
            element.style["background-image"] = "";
            parts.gradient = backgroundImageCssToParts(
                // Compute the style from o_cc class.
                getComputedStyle(element).backgroundImage
            ).gradient;
            element.style["background-image"] = backgroundImagePartsToCss(parts);
        }
    }

    getColorCombination(el, actionParam) {
        for (const handler of this.getResource("color_combination_getters")) {
            const value = handler(el, actionParam);
            if (value) {
                return value;
            }
        }
    }
}

function getColorCombinationFromClass(el) {
    return el.className.match?.(COLOR_COMBINATION_CLASSES_REGEX)?.[0];
}

/**
 * Remove the gradient of the element only if it is the inheritance from the o_cc selector.
 */
function removePresetGradient(element) {
    const oldBackgroundImage = element.style["background-image"];
    const parts = backgroundImageCssToParts(oldBackgroundImage);
    const currentGradient = parts.gradient;
    element.style.removeProperty("background-image");
    const styleWithoutGradient = getComputedStyle(element);
    const presetGradient = backgroundImageCssToParts(styleWithoutGradient.backgroundImage).gradient;
    if (presetGradient !== currentGradient) {
        const withGradient = backgroundImagePartsToCss(parts);
        element.style["background-image"] = withGradient === "none" ? "" : withGradient;
    } else {
        delete parts.gradient;
        const withoutGradient = backgroundImagePartsToCss(parts);
        element.style["background-image"] = withoutGradient === "none" ? "" : withoutGradient;
    }
}
