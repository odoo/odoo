import { Plugin } from "@html_editor/plugin";
import {
    BG_CLASSES_REGEX,
    COLOR_COMBINATION_CLASSES_REGEX,
    getColorOrClass,
    hasAnyNodesColor,
    hasColor,
    TEXT_CLASSES_REGEX,
} from "@html_editor/utils/color";
import { fillEmpty, removeStyle, unwrapContents } from "@html_editor/utils/dom";
import {
    isEmptyBlock,
    isPhrasingContent,
    isRedundantElement,
    isTextNode,
    isVisibleTextNode,
    isWhitespace,
    isZWS,
} from "@html_editor/utils/dom_info";
import {
    closestElement,
    descendants,
    findUpTo,
    selectElements,
} from "@html_editor/utils/dom_traversal";
import { isColorGradient, normalizeCSSColor } from "@web/core/utils/colors";
import { backgroundImageCssToParts, backgroundImagePartsToCss } from "@html_editor/utils/image";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { closestBlock, isBlock } from "@html_editor/utils/blocks";
import { callbacksForCursorUpdate } from "@html_editor/utils/selection";

const COLOR_COMBINATION_CLASSES = [1, 2, 3, 4, 5].map((i) => `o_cc${i}`);
const COLOR_COMBINATION_SELECTOR = COLOR_COMBINATION_CLASSES.map((c) => `.${c}`).join(", ");

/**
 * @typedef { Object } ColorShared
 * @property { ColorPlugin['colorElement'] } colorElement
 * @property { ColorPlugin['removeAllColor'] } removeAllColor
 * @property { ColorPlugin['getElementColors'] } getElementColors
 * @property { ColorPlugin['applyColor'] } applyColor
 * @property { ColorPlugin['requestColor'] } requestColor
 * @property { ColorPlugin['getActiveColorInfo'] } getActiveColorInfo
 */

/**
 * @typedef {((element: HTMLElement, cssProp: string, color: string, params: Object) => boolean)[]} apply_color_style_overrides
 * @typedef {((color: string, mode: "color" | "backgroundColor") => void)[]} apply_color_overrides
 * @typedef {((color: string, mode: "color" | "backgroundColor") => string)[]} apply_background_color_processors
 * @typedef {((color: string) => string)[]} background_color_processors
 * @typedef {((element: HTMLElement) => void)[]} before_color_element_processors
 * @typedef {(() => void)[]} on_color_requested_handlers
 *
 * @typedef {((el: HTMLElement, actionParam: string) => string)[]} color_combination_providers
 */

export class ColorPlugin extends Plugin {
    static id = "color";
    static dependencies = ["selection", "split", "history", "format", "delete"];
    static shared = [
        "colorElement",
        "removeAllColor",
        "getElementColors",
        "getColorCombination",
        "applyColor",
        "requestColor",
        "getActiveColorInfo",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "applyColor",
                run: ({ color, mode }) => {
                    this.requestColor(color, mode);
                    this.dependencies.history.commit();
                },
                isAvailable: isHtmlContentSupported,
            },
        ],
        /** Handlers */
        on_all_formats_removed_handlers: this.removeAllColor.bind(this),
        on_collapsed_formats_removed_handlers: this.removeAllColor.bind(this),
        color_combination_providers: getColorCombinationFromClass,
        on_beforeinput_handlers: this.onBeforeInput.bind(this),
        before_insert_handlers: this.beforeInsert.bind(this),
        on_selectionchange_handlers: this.clearPendingColors.bind(this),
        on_deleted_handlers: this.convertEmptyColorToPendingIntent.bind(this),

        /** Predicates */
        has_format_predicates: (node) => {
            const el = closestElement(node);
            if (hasColor(el, "color") || hasColor(el, "backgroundColor")) {
                return true;
            }
        },
        is_format_class_predicates: (className) => {
            if (TEXT_CLASSES_REGEX.test(className) || BG_CLASSES_REGEX.test(className)) {
                return true;
            }
        },

        /** Processors */
        normalize_processors: this.normalize.bind(this),
    };

    setup() {
        this.activeColorInfo = {};
    }

    normalize(root) {
        for (const el of selectElements(root, "font")) {
            if (isRedundantElement(el)) {
                unwrapContents(el);
            }
        }
        return root;
    }

    getActiveColorInfo() {
        return this.activeColorInfo;
    }

    onBeforeInput(ev) {
        if (ev.inputType === "insertText") {
            const selection = this.dependencies.selection.getEditableSelection();
            if (!selection.isCollapsed) {
                return;
            }
            this.applyPendingColors();
        }
    }

    beforeInsert() {
        const selection = this.dependencies.selection.getEditableSelection();
        if (selection.isCollapsed) {
            this.applyPendingColors();
        }
    }

    /**
     * Discard pending color intents when the selection changes.
     */
    clearPendingColors() {
        if (this.skipNextColorClear) {
            this.skipNextColorClear = false;
            return;
        }
        this.activeColorInfo = {};
    }

    applyPendingColors() {
        for (const [mode, color] of Object.entries(this.activeColorInfo)) {
            this.applyColor(color, mode);
        }
    }

    getElementColors(el) {
        const elStyle = getComputedStyle(el);
        const backgroundImage = elStyle.backgroundImage;
        const gradient = backgroundImageCssToParts(backgroundImage).gradient;
        const hasGradient = isColorGradient(gradient);
        const hasTextGradientClass = el.classList.contains("text-gradient");

        const backgroundColor = this.processThrough(
            "background_color_processors",
            elStyle.backgroundColor
        );

        return {
            color:
                hasGradient && hasTextGradientClass ? gradient : normalizeCSSColor(elStyle.color),
            backgroundColor:
                hasGradient && !hasTextGradientClass
                    ? gradient
                    : normalizeCSSColor(backgroundColor),
        };
    }

    removeAllColor() {
        const sel = this.dependencies.selection.getEditableSelection();
        if (sel.isCollapsed) {
            const el = closestElement(sel.anchorNode);
            const block = closestBlock(sel.anchorNode);
            for (const mode of ["color", "backgroundColor"]) {
                if (findUpTo(el, block, (node) => getColorOrClass(node, mode))) {
                    this.activeColorInfo[mode] = "";
                }
            }
            this.skipNextColorClear = true;
            this.trigger("on_color_requested_handlers");
            return;
        }
        this.activeColorInfo = {};
        const colorModes = ["color", "backgroundColor"];
        const colorNodeProviders = this.getResource("color_target_providers");
        let someColorWasRemoved = true;
        while (someColorWasRemoved) {
            someColorWasRemoved = false;
            for (const mode of colorModes) {
                let max = 40;
                const hasAnySelectedNodeColor = (mode) => {
                    const nodes = new Set();
                    const editableTargetedNodes = this.dependencies.selection
                        .getTargetedNodes()
                        .filter(this.dependencies.selection.isNodeEditable);
                    for (const node of editableTargetedNodes) {
                        for (const getColorNode of colorNodeProviders) {
                            const colorNode = getColorNode(node);
                            if (colorNode) {
                                nodes.add(colorNode);
                            }
                        }
                        if (isTextNode(node)) {
                            nodes.add(node);
                        }
                    }
                    return hasAnyNodesColor([...nodes], mode);
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

    requestColor(color, mode, previewMode = false) {
        const sel = this.dependencies.selection.getEditableSelection();
        if (sel.isCollapsed) {
            const block = closestBlock(sel.anchorNode);
            const colorNode = findUpTo(closestElement(sel.anchorNode), block, (node) =>
                getColorOrClass(node, mode)
            );
            const current = colorNode && getColorOrClass(colorNode, mode);
            if ((current?.value ?? "") === color) {
                delete this.activeColorInfo[mode];
            } else {
                this.activeColorInfo[mode] = color;
            }
            this.skipNextColorClear = true;
            this.trigger("on_color_requested_handlers");
            return;
        }
        this.applyColor(color, mode, previewMode);
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
            color = this.processThrough("apply_background_color_processors", color, mode);
        }
        const coloredNodes = new Set();
        if (this.delegateTo("apply_color_overrides", color, mode, coloredNodes, previewMode)) {
            return;
        }
        const selection = this.dependencies.selection.getEditableSelection();
        let targetedNodes;
        // Get the <font> nodes to color
        if (selection.isCollapsed) {
            const zws = this.dependencies.format.getOrCreateZws();
            this.dependencies.selection.setSelection(
                {
                    anchorNode: zws,
                    anchorOffset: 1,
                },
                { normalize: false }
            );
            targetedNodes = [zws];
        } else {
            this.dependencies.split.splitSelection();
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
        const cursors = this.dependencies.selection.preserveSelection();

        const findTopMostDecoration = (current) => {
            const decoration = closestElement(current.parentNode, "s, u");
            return decoration?.textContent === current.textContent
                ? findTopMostDecoration(decoration)
                : current;
        };

        const systemNodesSelector = this.getResource("system_node_selectors").join(", ");
        const selectedNodes = targetedNodes
            .filter(
                (node) =>
                    !coloredNodes.has(node) &&
                    !(systemNodesSelector && closestElement(node, systemNodesSelector)) &&
                    (this.checkPredicates("is_formattable_node_predicates", node) ?? true)
            )
            .map((node) => findTopMostDecoration(node));

        const alreadyWithinFont = new Set();
        const getFonts = (selectedNodes) =>
            selectedNodes.flatMap((node) => {
                // The node is already within a newly created font so we filter
                // it out.
                if (alreadyWithinFont.has(node)) {
                    return [];
                }
                // Background gradient cannot be applied within text gradient.
                const shouldBreakGradient = (node) =>
                    mode === "backgroundColor" &&
                    isColorGradient(color) &&
                    node.classList.contains("text-gradient");
                let font = closestElement(
                    node,
                    (node) =>
                        (hasColor(node, mode) || shouldBreakGradient(node)) &&
                        node.nodeName !== "LI"
                );
                if (
                    color &&
                    font &&
                    !shouldBreakGradient(font) &&
                    // Partially selected gradient font
                    ((isColorGradient(font.style["background-image"]) &&
                        !this.dependencies.selection.areNodeContentsFullySelected(font)) ||
                        // Gradient found between node uptil font
                        findUpTo(node, font, (ancestor) =>
                            isColorGradient(ancestor.style?.["background-image"])
                        ))
                ) {
                    font = null;
                }
                const children = font && descendants(font);
                if (font && !this.dependencies.split.isUnsplittable(font)) {
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
                            for (const child of [...font.childNodes]) {
                                cursors.update(callbacksForCursorUpdate.append(newFont, child));
                                newFont.append(child);
                            }
                            cursors.update(callbacksForCursorUpdate.append(font, newFont));
                            font.append(newFont);
                            font = newFont;
                        }
                        font = this.dependencies.split.splitAroundUntil(selectedChildren, font);
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
                        cursors.update(callbacksForCursorUpdate.after(node, font));
                        node.after(font);
                    }
                    if (node.textContent) {
                        cursors.update(callbacksForCursorUpdate.append(font, node));
                        font.appendChild(node);
                        if (isTextNode(node) && isZWS(node)) {
                            font.setAttribute("data-oe-zws-empty-inline", "");
                        }
                        descendants(node).forEach((n) => alreadyWithinFont.add(n));
                    } else {
                        fillEmpty(font);
                    }
                } else {
                    font = []; // Ignore non-text or invisible text nodes.
                }
                return font;
            });

        let fonts = getFonts(selectedNodes);
        // Dirty fix as the previous call could have unconnected elements
        // because of the `splitAroundUntil`. Another call should provide he
        // correct list of fonts.
        if (!fonts.every((font) => font.isConnected)) {
            fonts = getFonts(selectedNodes);
        }

        // Color the selected <font>s and remove uncolored fonts.
        const fontsSet = new Set(fonts);
        delete this.activeColorInfo[mode];
        for (const font of fontsSet) {
            this.colorElement(font, color, mode);
            if (
                !hasColor(font, "color") &&
                !hasColor(font, "backgroundColor") &&
                ["FONT", "SPAN"].includes(font.nodeName) &&
                (!font.hasAttribute("style") || !color)
            ) {
                const parent = font.parentNode;
                if (
                    font.childNodes.length === 1 &&
                    isTextNode(font.firstChild) &&
                    isZWS(font.firstChild)
                ) {
                    cursors.update(callbacksForCursorUpdate.remove(font));
                    font.remove();
                } else {
                    cursors.update(callbacksForCursorUpdate.unwrap(font));
                    unwrapContents(font);
                }
                fillEmpty(parent);
                fontsSet.delete(font);
            }
        }
        cursors.restore();
    }

    convertEmptyColorToPendingIntent() {
        const selection = this.dependencies.selection.getEditableSelection();
        const anchorNode = selection.anchorNode;
        let element = closestElement(anchorNode);
        const cursor = this.dependencies.selection.preserveSelection();
        while (
            isZWS(element) &&
            isPhrasingContent(element) &&
            !this.dependencies.delete.isUnremovable(element)
        ) {
            const color = getColorOrClass(element, "color");
            const bgColor = getColorOrClass(element, "backgroundColor");
            if (!color && !bgColor) {
                break;
            }
            const parent = element.parentElement;
            if (color) {
                this.activeColorInfo.color = color.value;
                this.colorElement(element, "", "color");
            }
            if (bgColor) {
                this.activeColorInfo.backgroundColor = bgColor.value;
                this.colorElement(element, "", "backgroundColor");
            }
            const nonZwsAttrs = element
                .getAttributeNames()
                .filter((attr) => attr !== "data-oe-zws-empty-inline");
            if (["FONT", "SPAN"].includes(element.nodeName) && !nonZwsAttrs.length) {
                cursor.update(callbacksForCursorUpdate.unwrap(element));
                unwrapContents(element);
            }
            element = parent;
        }
        if (
            Object.keys(this.activeColorInfo).length &&
            anchorNode.isConnected &&
            anchorNode.nodeType === Node.TEXT_NODE &&
            anchorNode.textContent === "\u200b"
        ) {
            cursor.update(callbacksForCursorUpdate.remove(anchorNode));
            anchorNode.remove();
            this.skipNextColorClear = true;
        }
        cursor.restore();
    }

    /**
     * Applies a css or class color (fore- or background-) to an element.
     * Replace the color that was already there if any.
     *
     * @param {Element} element
     * @param {string} color hexadecimal or bg-name/text-name class
     * @param {'color'|'backgroundColor'} mode 'color' or 'backgroundColor'
     * @param {Object} params additional parameters
     */
    colorElement(element, color, mode, params = {}) {
        this.processThrough("before_color_element_processors", element);
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
            removeStyle(element, "background-color");
        }

        const newClassName = oldClassName
            .replace(mode === "color" ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX, "")
            .replace(/\btext-gradient\b/g, "") // cannot be combined with setting a background
            .replace(/\s+/, " ");
        if (oldClassName !== newClassName) {
            element.setAttribute("class", newClassName);
        }
        const isTextGradient = closestElement(element, ".text-gradient");
        // If the nearest <font> has a text gradient, its
        // visible color comes from -webkit-text-fill-color,
        // we need to set it too when applying a color.
        if (isTextGradient && mode === "color" && !isColorGradient(color)) {
            element.style.webkitTextFillColor = color;
        } else if (isColorGradient(color) || color === "") {
            removeStyle(element, "-webkit-text-fill-color");
        }
        if (isColorGradient(color)) {
            removeStyle(element, mode === "backgroundColor" ? "background-color" : mode);
            parts.gradient = color;
            if (mode === "color") {
                removeStyle(element, "background-color");
                element.classList.add("text-gradient");
            } else {
                // When a gradient is applied as background-image, explicitly set
                // background-color: transparent. This overrides o_cc(x) background,
                // allowing gradient with transparency to show the content
                // underneath.
                element.style["background-color"] = "transparent";
            }
            this.applyColorStyle(
                element,
                "background-image",
                backgroundImagePartsToCss(parts),
                params
            );
        } else {
            delete parts.gradient;
            if (hasGradientStyle && !backgroundImagePartsToCss(parts)) {
                removeStyle(element, "background-image");
            }
            if (color.startsWith("text") || color.startsWith("bg-")) {
                removeStyle(element, mode);
                element.classList.add(color);
            } else {
                // Change camelCase to kebab-case.
                mode = mode.replace("backgroundColor", "background-color");
                this.applyColorStyle(element, mode, color, params);
            }
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
            removeStyle(element, "background-image");
            parts.gradient = backgroundImageCssToParts(
                // Compute the style from o_cc class.
                getComputedStyle(element).backgroundImage
            ).gradient;
            element.style["background-image"] = backgroundImagePartsToCss(parts);
        }
    }

    getColorCombination(el, actionParam) {
        for (const handler of this.getResource("color_combination_providers")) {
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
     * @param {Object} params additional parameters
     */
    applyColorStyle(element, mode, color, params = {}) {
        if (this.delegateTo("apply_color_style_overrides", element, mode, color, params)) {
            return;
        }
        if (color) {
            element.style[mode] = color;
        } else {
            removeStyle(element, mode);
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
