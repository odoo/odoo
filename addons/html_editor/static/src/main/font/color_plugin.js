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
    isEmptyBlock,
    isRedundantElement,
    isTextNode,
    isVisibleTextNode,
    isWhitespace,
    isZWS,
} from "@html_editor/utils/dom_info";
import { closestElement, descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { isColorGradient, rgbaToHex } from "@web/core/utils/colors";
import { backgroundImageCssToParts, backgroundImagePartsToCss } from "@html_editor/utils/image";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { isBlock } from "@html_editor/utils/blocks";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

const COLOR_COMBINATION_CLASSES = [1, 2, 3, 4, 5].map((i) => `o_cc${i}`);
const COLOR_COMBINATION_SELECTOR = COLOR_COMBINATION_CLASSES.map((c) => `.${c}`).join(", ");

/**
 * @typedef { Object } ColorShared
 * @property { ColorPlugin['colorElement'] } colorElement
 * @property { ColorPlugin['removeAllColor'] } removeAllColor
 * @property { ColorPlugin['getElementColors'] } getElementColors
 * @property { ColorPlugin['applyColor'] } applyColor
 */

/**
 * @typedef {((element: HTMLElement, cssProp: string, color: string) => boolean)[]} apply_color_style_overrides
 * @typedef {((color: string, mode: "color" | "backgroundColor") => void)[]} color_apply_overrides
 * @typedef {((color: string, mode: "color" | "backgroundColor") => string)[]} apply_background_color_processors
 * @typedef {((color: string) => string)[]} get_background_color_processors
 *
 * @typedef {((el: HTMLElement, actionParam: string) => string)[]} color_combination_getters
 */

export class ColorPlugin extends Plugin {
    static id = "color";
    static dependencies = ["selection", "split", "history", "format"];
    static shared = [
        "colorElement",
        "removeAllColor",
        "getElementColors",
        "getColorCombination",
        "applyColor",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "applyColor",
                run: ({ color, mode }) => {
                    this.applyColor(color, mode);
                    this.dependencies.history.addStep();
                },
                isAvailable: isHtmlContentSupported,
            },
        ],
        /** Handlers */
        remove_all_formats_handlers: this.removeAllColor.bind(this),
        color_combination_getters: getColorCombinationFromClass,

        /** Predicates */
        has_format_predicates: [
            (node) => hasColor(closestElement(node), "color"),
            (node) => hasColor(closestElement(node), "backgroundColor"),
        ],
        format_class_predicates: (className) =>
            TEXT_CLASSES_REGEX.test(className) || BG_CLASSES_REGEX.test(className),
        normalize_handlers: this.normalize.bind(this),
    };

    normalize(root) {
        for (const el of selectElements(root, "font")) {
            if (isRedundantElement(el)) {
                unwrapContents(el);
            }
        }
    }

    getElementColors(el) {
        const elStyle = getComputedStyle(el);
        const backgroundImage = elStyle.backgroundImage;
        const gradient = backgroundImageCssToParts(backgroundImage).gradient;
        const hasGradient = isColorGradient(gradient);
        const hasTextGradientClass = el.classList.contains("text-gradient");

        let backgroundColor = elStyle.backgroundColor;
        for (const processor of this.getResource("get_background_color_processors")) {
            backgroundColor = processor(backgroundColor);
        }

        return {
            color: hasGradient && hasTextGradientClass ? gradient : rgbaToHex(elStyle.color),
            backgroundColor:
                hasGradient && !hasTextGradientClass ? gradient : rgbaToHex(backgroundColor),
        };
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
                    this.applyColor("", mode);
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
    applyColor(color, mode, previewMode = false) {
        this.dependencies.selection.selectAroundNonEditable();
        if (mode === "backgroundColor") {
            for (const processor of this.getResource("apply_background_color_processors")) {
                color = processor(color, mode);
            }
        }
        if (this.delegateTo("color_apply_overrides", color, mode, previewMode)) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        let cursors;
        let targetedNodes;
        // Get the <font> nodes to color
        if (selection.isCollapsed) {
            let zws;
            if (
                selection.anchorNode.nodeType === Node.TEXT_NODE &&
                selection.anchorNode.textContent === "\u200b"
            ) {
                zws = selection.anchorNode;
            } else {
                zws = this.dependencies.format.insertAndSelectZws();
            }
            this.dependencies.selection.setSelection(
                {
                    anchorNode: zws,
                    anchorOffset: 0,
                },
                { normalize: false }
            );
            cursors = this.dependencies.selection.preserveSelection();
            targetedNodes = [zws];
        } else {
            this.dependencies.split.splitSelection();
            cursors = this.dependencies.selection.preserveSelection();
            targetedNodes = this.dependencies.selection
                .getTargetedNodes()
                .filter(
                    (node) =>
                        this.dependencies.selection.isNodeEditable(node) && node.nodeName !== "T"
                );
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
                if (closestElement(node).classList.contains("o_default_color")) {
                    return false;
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

                const faNodes = font?.querySelectorAll(".fa");
                if (faNodes && Array.from(faNodes).some((faNode) => faNode.contains(node))) {
                    return font;
                }
                const children = font && descendants(font);
                const hasInlineGradient = font && isColorGradient(font.style["background-image"]);
                const isFullySelected =
                    children && children.every((child) => selectedNodes.includes(child));
                const isTextGradient =
                    hasInlineGradient && font.classList.contains("text-gradient");
                const shouldReplaceExistingGradient =
                    isFullySelected &&
                    ((mode === "color" && isTextGradient) ||
                        (mode === "backgroundColor" && !isTextGradient));
                if (
                    font &&
                    font.nodeName !== "T" &&
                    (font.nodeName !== "SPAN" || font.style[mode] || font.style.backgroundImage) &&
                    (isColorGradient(color) ||
                        color === "" ||
                        !hasInlineGradient ||
                        shouldReplaceExistingGradient) &&
                    !this.dependencies.split.isUnsplittable(font)
                ) {
                    // Partially selected <font>: split it.
                    const selectedChildren = children.filter(
                        (child) => child.isConnected && selectedNodes.includes(child)
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
                            font.classList.forEach((className) => {
                                if (TEXT_CLASSES_REGEX.test(className)) {
                                    font.classList.remove(className);
                                    newFont.classList.add(className);
                                }
                            });
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
                                    closestGradientEl.classList.contains("text-gradient") &&
                                    !shouldReplaceExistingGradient))
                        ) {
                            font.style.webkitTextFillColor = color;
                        }
                    } else {
                        font = [];
                    }
                } else if (
                    (node.nodeType === Node.TEXT_NODE &&
                        (isVisibleTextNode(node) || isZWS(node))) ||
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
            this.colorElement(font, color, mode);
            if (
                !hasColor(font, "color") &&
                !hasColor(font, "backgroundColor") &&
                ["FONT", "SPAN"].includes(font.nodeName) &&
                (!font.hasAttribute("style") || !color)
            ) {
                cursors.update(callbacksForCursorUpdate.unwrap(font));
                unwrapContents(font);
                fontsSet.delete(font);
            }
        }
        cursors.restore();
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

        const hasGradientStyle = element.style.backgroundImage.includes("-gradient");
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
            this.applyColorStyle(element, "background-image", backgroundImagePartsToCss(parts));
        } else {
            delete parts.gradient;
            if (hasGradientStyle && !backgroundImagePartsToCss(parts)) {
                element.style["background-image"] = "";
            }
            // Change camelCase to kebab-case.
            mode = mode.replace("backgroundColor", "background-color");
            this.applyColorStyle(element, mode, color);
        }

        // It was decided that applying a color combination removes any "color"
        // value (custom color, color classes, gradients, ...). Changing any
        // "color", including color combinations, should still not remove the
        // other background layers though (image, video, shape, ...).
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

    /**
     * @param {Element} element
     * @param {string} cssProp
     * @param {string} cssValue
     */
    applyColorStyle(element, mode, color) {
        if (this.delegateTo("apply_color_style_overrides", element, mode, color)) {
            return;
        }
        element.style[mode] = color;
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
