/** @odoo-module native */
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { isBlock } from "@html_editor/utils/blocks";
import {
    BG_CLASSES_REGEX,
    COLOR_COMBINATION_CLASSES_REGEX,
    hasAnyNodesColor,
    hasColor,
    hasTextColorClass,
    TEXT_CLASSES_REGEX,
} from "@html_editor/utils/color";
import { fillEmpty, unwrapContents } from "@html_editor/utils/dom";
import {
    ICON_SELECTOR,
    isEmptyBlock,
    isRedundantElement,
    isTextNode,
    isVisibleTextNode,
    isWhitespace,
    isZWS,
} from "@html_editor/utils/dom_info";
import {
    closestElement,
    descendants,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import {
    backgroundImageCssToParts,
    backgroundImagePartsToCss,
} from "@html_editor/utils/image";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";
import { _t } from "@web/core/translation";
import {
    isColorGradient,
    normalizeCSSColor,
    rgbaToHex,
} from "@web/core/utils/format/colors";

const COLOR_COMBINATION_CLASSES = [1, 2, 3, 4, 5].map((i) => `o_cc${i}`);
const COLOR_COMBINATION_SELECTOR = COLOR_COMBINATION_CLASSES.map((c) => `.${c}`).join(
    ", ",
);

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
 * @typedef {((element: HTMLElement) => HTMLElement)[]} before_color_element_processors
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
        remove_all_formats_handlers: this.removeAllColor.bind(this),
        color_combination_getters: getColorCombinationFromClass,

        can_remove_format_predicates: [
            (targetedNodes) => {
                if (
                    targetedNodes.some((node) => hasColor(closestElement(node), "color"))
                ) {
                    return true;
                }
            },
            (targetedNodes) => {
                if (
                    targetedNodes.some((node) =>
                        hasColor(closestElement(node), "backgroundColor"),
                    )
                ) {
                    return true;
                }
            },
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
            color:
                hasGradient && hasTextGradientClass
                    ? gradient
                    : normalizeCSSColor(elStyle.color),
            backgroundColor:
                hasGradient && !hasTextGradientClass
                    ? gradient
                    : normalizeCSSColor(backgroundColor),
        };
    }

    removeAllColor() {
        const colorModes = ["color", "backgroundColor"];

        for (const icon of this.getTargetedIcons()) {
            for (const mode of colorModes) {
                this.colorElement(icon, "", mode);
            }
        }

        let someColorWasRemoved = true;
        while (someColorWasRemoved) {
            someColorWasRemoved = false;
            for (const mode of colorModes) {
                let max = 40;
                while (this.hasAnySelectedNodeColor(mode) && max > 0) {
                    this.applyColor("", mode);
                    someColorWasRemoved = true;
                    max--;
                }
                if (max === 0) {
                    this.services?.notification?.add?.(
                        _t("Some colors could not be removed."),
                        { type: "warning" },
                    );
                    return;
                }
            }
        }
    }

    /**
     * @returns {HTMLElement[]}
     */
    getTargetedIcons() {
        const icons = [];
        for (const node of this.dependencies.selection.getTargetedNodes()) {
            const icon =
                node.nodeType === Node.ELEMENT_NODE && node.matches?.(ICON_SELECTOR)
                    ? node
                    : closestElement(node, ICON_SELECTOR);
            if (
                icon &&
                !icons.includes(icon) &&
                this.dependencies.selection.isNodeEditable(icon)
            ) {
                icons.push(icon);
            }
        }
        return icons;
    }

    /**
     * @param {"color"|"backgroundColor"} mode
     * @returns {boolean}
     */
    hasAnySelectedNodeColor(mode) {
        const nodes = this.dependencies.selection
            .getTargetedNodes()
            .filter(
                (n) =>
                    this.dependencies.selection.isNodeEditable(n) &&
                    (isTextNode(n) ||
                        (mode === "backgroundColor" &&
                            n.classList?.contains("o_selected_td"))),
            );
        return hasAnyNodesColor(nodes, mode);
    }

    /**
     * @param {string} color
     * @param {string} mode
     * @param {boolean} [previewMode=false]
     */
    applyColor(color, mode, previewMode = false) {
        this.dependencies.selection.selectAroundNonEditable();
        if (mode === "backgroundColor") {
            for (const processor of this.getResource(
                "apply_background_color_processors",
            )) {
                color = processor(color, mode);
            }
        }
        if (this.delegateTo("color_apply_overrides", color, mode, previewMode)) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        let cursors;
        let targetedNodes;
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
                    anchorOffset: 1,
                },
                { normalize: false },
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
                        this.dependencies.selection.isNodeEditable(node) &&
                        node.nodeName !== "T",
                );
            if (isEmptyBlock(selection.endContainer)) {
                targetedNodes.push(
                    selection.endContainer,
                    ...descendants(selection.endContainer),
                );
            }
        }

        const findTopMostDecoration = (current) => {
            const decoration = closestElement(current.parentNode, "s, u");
            return decoration?.textContent === current.textContent
                ? findTopMostDecoration(decoration)
                : current;
        };

        const hexColor = rgbaToHex(color).toLowerCase();
        const systemNodesSelector = this.getResource("system_node_selectors").join(
            ", ",
        );
        const selectedNodes = targetedNodes
            .filter((node) => {
                if (systemNodesSelector && closestElement(node, systemNodesSelector)) {
                    return false;
                }
                if (!(
                    this.checkPredicates("is_formattable_node_predicates", node) ?? true
                )) {
                    return false;
                }
                if (mode === "backgroundColor" && color) {
                    return !closestElement(node, "table.o_selected_table");
                }
                if (closestElement(node).classList.contains("o_default_color")) {
                    return false;
                }
                const li = closestElement(node, "li");
                if (
                    li &&
                    color &&
                    this.dependencies.selection.areNodeContentsFullySelected(li)
                ) {
                    return rgbaToHex(li.style.color).toLowerCase() !== hexColor;
                }
                return true;
            })
            .map((node) => findTopMostDecoration(node));

        const targetedFieldNodes = new Set(
            this.dependencies.selection
                .getTargetedNodes()
                .map((n) => closestElement(n, "*[t-field],*[t-out],*[t-esc]"))
                .filter(Boolean),
        );

        const getFonts = (selectedNodes) =>
            selectedNodes.flatMap((node) => {
                let font =
                    closestElement(node, "font") ||
                    closestElement(
                        node,
                        '[style*="color"]:not(li), [style*="background-color"]:not(li), [style*="background-image"]:not(li)',
                    ) ||
                    closestElement(node, "span") ||
                    closestElement(
                        node,
                        (node) =>
                            node.nodeName !== "LI" && hasTextColorClass(node, mode),
                    );

                const faNodes = font?.querySelectorAll(ICON_SELECTOR);
                if (
                    faNodes &&
                    Array.from(faNodes).some((faNode) => faNode.contains(node))
                ) {
                    return font;
                }
                const children = font && descendants(font);
                const hasInlineGradient =
                    font && isColorGradient(font.style["background-image"]);
                const isFullySelected =
                    children &&
                    children.every((child) => selectedNodes.includes(child));
                const isFullySelectedIgnoringScaffolding =
                    children &&
                    children.every(
                        (child) =>
                            selectedNodes.includes(child) ||
                            (child.nodeType === Node.TEXT_NODE &&
                                !child.textContent
                                    .replace(/[\u200B\uFEFF]/g, "")
                                    .trim()),
                    );
                const isTextGradient =
                    hasInlineGradient && font.classList.contains("text-gradient");
                const shouldReplaceExistingGradient =
                    isFullySelected &&
                    ((mode === "color" && isTextGradient) ||
                        (mode === "backgroundColor" && !isTextGradient));
                if (
                    font &&
                    font.nodeName !== "T" &&
                    (font.nodeName !== "SPAN" ||
                        font.style[mode] ||
                        font.style.backgroundImage ||
                        hasTextColorClass(font, mode)) &&
                    (isColorGradient(color) ||
                        color === "" ||
                        !hasInlineGradient ||
                        shouldReplaceExistingGradient) &&
                    (isFullySelectedIgnoringScaffolding ||
                        !this.dependencies.split.isUnsplittable(font))
                ) {
                    const selectedChildren = children.filter(
                        (child) => child.isConnected && selectedNodes.includes(child),
                    );
                    if (selectedChildren.length) {
                        if (isBlock(font)) {
                            const colorStyles = [
                                "color",
                                "background-color",
                                "background-image",
                            ];
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
                            'font[style*="background-image"], span[style*="background-image"]',
                        );
                        const isGradientBeingUpdated =
                            closestGradientEl && isColorGradient(color);
                        const splitnode = isGradientBeingUpdated
                            ? closestGradientEl
                            : font;
                        font = this.dependencies.split.splitAroundUntil(
                            selectedChildren,
                            splitnode,
                        );
                        if (isGradientBeingUpdated) {
                            const classRegex =
                                mode === "color"
                                    ? TEXT_CLASSES_REGEX
                                    : BG_CLASSES_REGEX;
                            for (const node of descendants(font)) {
                                if (
                                    node.nodeType === Node.ELEMENT_NODE &&
                                    (node.style[mode] ||
                                        classRegex.test(node.className))
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
                                    closestGradientEl.classList.contains(
                                        "text-gradient",
                                    ) &&
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
                        ["inline", "inline-block"].includes(
                            getComputedStyle(node).display,
                        ) &&
                        !isWhitespace(node.textContent) &&
                        !node.classList.contains("btn") &&
                        !node.querySelector("font") &&
                        node.nodeName !== "A" &&
                        !(node.nodeName === "SPAN" && node.style["fontSize"]))
                ) {
                    const previous = node.previousSibling;
                    const classRegex =
                        mode === "color" ? BG_CLASSES_REGEX : TEXT_CLASSES_REGEX;
                    if (
                        previous &&
                        previous.nodeName === "FONT" &&
                        !previous.style[
                            mode === "color" ? "backgroundColor" : "color"
                        ] &&
                        !classRegex.test(previous.className) &&
                        selectedNodes.includes(previous.firstChild) &&
                        selectedNodes.includes(previous.lastChild)
                    ) {
                        font = previous;
                    } else {
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
                    font = [];
                }
                return font;
            });

        for (const fieldNode of targetedFieldNodes) {
            this.colorElement(fieldNode, color, mode);
        }

        let fonts = getFonts(selectedNodes);
        if (!fonts.every((font) => font.isConnected)) {
            fonts = getFonts(selectedNodes);
        }

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
     * @param {Element} element
     * @param {string} color
     * @param {'color'|'backgroundColor'} mode
     */
    colorElement(element, color, mode) {
        for (const processor of this.getResource("before_color_element_processors")) {
            element = processor(element);
        }
        const parts = backgroundImageCssToParts(element.style["background-image"]);
        const oldClassName = element.getAttribute("class") || "";

        if (element.matches(COLOR_COMBINATION_SELECTOR)) {
            removePresetGradient(element);
        }

        const hasGradientStyle = element.style.backgroundImage.includes("-gradient");
        if (mode === "backgroundColor") {
            if (!color) {
                element.classList.remove("o_cc", ...COLOR_COMBINATION_CLASSES);
            }
            const hasGradient =
                getComputedStyle(element).backgroundImage.includes("-gradient");
            delete parts.gradient;
            let newBackgroundImage = backgroundImagePartsToCss(parts);
            if (hasGradient && !newBackgroundImage) {
                newBackgroundImage = "none";
            }
            element.style.backgroundImage = newBackgroundImage;
            element.style["background-color"] = "";
        }

        const newClassName = oldClassName
            .replace(mode === "color" ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX, "")
            .replace(/\btext-gradient\b/g, "")
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
            this.applyColorStyle(
                element,
                "background-image",
                backgroundImagePartsToCss(parts),
            );
        } else {
            delete parts.gradient;
            if (hasGradientStyle && !backgroundImagePartsToCss(parts)) {
                element.style["background-image"] = "";
            }
            mode = mode.replace("backgroundColor", "background-color");
            this.applyColorStyle(element, mode, color);
        }

        if (color.startsWith("o_cc")) {
            element.classList.remove(...COLOR_COMBINATION_CLASSES);
            element.classList.add("o_cc", color);

            const hasBackgroundColor = !!getComputedStyle(element).backgroundColor;
            const hasGradient =
                getComputedStyle(element).backgroundImage.includes("-gradient");
            const backgroundImage = element.style["background-image"];
            if (hasBackgroundColor && hasGradient && !backgroundImage) {
                element.style.backgroundImage = "none";
            }
        }

        this.fixColorCombination(element, color);
    }
    fixColorCombination(element, color) {
        const parts = backgroundImageCssToParts(element.style["background-image"]);
        const hasBackgroundColor =
            element.style["background-color"] ||
            !!element.className.match(/\bbg-/) ||
            parts.gradient;

        if (
            !hasBackgroundColor &&
            (isColorGradient(color) || color.startsWith("o_cc"))
        ) {
            element.style["background-image"] = "";
            parts.gradient = backgroundImageCssToParts(
                getComputedStyle(element).backgroundImage,
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
     * @param {string} mode
     * @param {string} color
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

function removePresetGradient(element) {
    const oldBackgroundImage = element.style["background-image"];
    const parts = backgroundImageCssToParts(oldBackgroundImage);
    const currentGradient = parts.gradient;
    element.style.removeProperty("background-image");
    const styleWithoutGradient = getComputedStyle(element);
    const presetGradient = backgroundImageCssToParts(
        styleWithoutGradient.backgroundImage,
    ).gradient;
    if (presetGradient !== currentGradient) {
        const withGradient = backgroundImagePartsToCss(parts);
        element.style["background-image"] = withGradient === "none" ? "" : withGradient;
    } else {
        delete parts.gradient;
        const withoutGradient = backgroundImagePartsToCss(parts);
        element.style["background-image"] =
            withoutGradient === "none" ? "" : withoutGradient;
    }
}
