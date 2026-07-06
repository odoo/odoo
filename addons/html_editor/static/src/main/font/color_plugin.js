import { Plugin } from "@html_editor/plugin";
import {
    BG_CLASSES_REGEX,
    COLOR_COMBINATION_CLASSES_REGEX,
    getColorOrClass,
    hasAnyNodesColor,
    hasColor,
    TEXT_CLASSES_REGEX,
} from "@html_editor/utils/color";
import { removeClass, removeStyle, unwrapContents } from "@html_editor/utils/dom";
import { isRedundantElement, isTextNode } from "@html_editor/utils/dom_info";
import { closestElement, findUpTo, selectElements } from "@html_editor/utils/dom_traversal";
import { closestBlock } from "@html_editor/utils/blocks";
import { isColorGradient, normalizeCSSColor } from "@web/core/utils/colors";
import { backgroundImageCssToParts, backgroundImagePartsToCss } from "@html_editor/utils/image";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

const COLOR_COMBINATION_CLASSES = [1, 2, 3, 4, 5].map((i) => `o_cc${i}`);
const COLOR_COMBINATION_SELECTOR = COLOR_COMBINATION_CLASSES.map((c) => `.${c}`).join(", ");

/**
 * @typedef { Object } ColorShared
 * @property { ColorPlugin['colorElement'] } colorElement
 * @property { ColorPlugin['removeAllColor'] } removeAllColor
 * @property { ColorPlugin['getElementColors'] } getElementColors
 */

/**
 * @typedef {((element: HTMLElement, cssProp: string, color: string, params: Object) => boolean)[]} apply_color_style_overrides
 * @typedef {((color: string) => string)[]} background_color_processors
 * @typedef {((element: HTMLElement) => void)[]} before_color_element_processors
 *
 * @typedef {((el: HTMLElement, actionParam: string) => string)[]} color_combination_providers
 */

export class ColorPlugin extends Plugin {
    static id = "color";
    static dependencies = ["selection", "split", "history", "format", "delete"];
    static shared = ["colorElement", "removeAllColor", "getElementColors", "getColorCombination"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "applyColor",
                run: ({ color, mode }) => {
                    this.dependencies.format.requestFormat(mode, {
                        applyStyle: color !== "",
                        formatProps: color ? { color } : undefined,
                    });
                },
                isAvailable: isHtmlContentSupported,
            },
        ],
        format_specs: ["color", "backgroundColor"].map((mode) => ({
            id: mode,
            isFormatted: (node, formatProps) => {
                const el = closestElement(node);
                if (formatProps) {
                    return getColorOrClass(el, mode)?.value === formatProps.color;
                }
                return !!findUpTo(el, closestBlock(el).parentElement, (n) => hasColor(n, mode));
            },
            removeStyle: (node) => {
                const el = closestElement(node);
                this.colorElement(el, "", mode);
                removeClass(el, "o_default_color");
            },
            hasStyle: (node) => !!getColorOrClass(closestElement(node), mode),
            addStyle: (node, props) => {
                this.colorElement(node, props.color, mode);
            },
            ...(mode === "color" && {
                addNeutralStyle: (node) => node.classList.add("o_default_color"),
            }),
            getFormatProps: (node) => {
                const el = closestElement(node);
                const value = getColorOrClass(el, mode)?.value;
                if (value) {
                    return { color: value };
                }
            },
        })),
        /** Handlers */
        on_all_formats_removed_handlers: this.removeAllColor.bind(this),
        color_combination_providers: getColorCombinationFromClass,

        /** Predicates */
        can_remove_format_predicates: (editableTargetedNodes) => {
            if (
                editableTargetedNodes.some((node) => {
                    const el = closestElement(node);
                    return el && (hasColor(el, "color") || hasColor(el, "backgroundColor"));
                })
            ) {
                return true;
            }
        },
        is_format_class_predicates: (className) => {
            if (TEXT_CLASSES_REGEX.test(className) || BG_CLASSES_REGEX.test(className)) {
                return true;
            }
        },
        is_format_splittable_predicates: (ancestor, formatName, formatProps) => {
            // Over: non gradient, applying: any mode => split
            if (!isColorGradient(ancestor.style["background-image"])) {
                return;
            }
            if (formatName === "color" || formatName === "backgroundColor") {
                const gradientMode = ancestor.classList.contains("text-gradient")
                    ? "color"
                    : "backgroundColor";
                // Over: gradient, same mode, removing => split, fully selected => split
                if (
                    gradientMode === formatName &&
                    (!formatProps?.color ||
                        this.dependencies.selection.areNodeContentsFullySelected(ancestor))
                ) {
                    return;
                }
                // Over: text-gradient, applying: backgroundColor gradient => split
                // Reason: it can't be rendered correctly.
                if (
                    gradientMode === "color" &&
                    formatName === "backgroundColor" &&
                    isColorGradient(formatProps?.color)
                ) {
                    return;
                }
                // Over: text-gradient, removing: backgroundColor painted above => split
                if (
                    gradientMode === "color" &&
                    formatName === "backgroundColor" &&
                    !formatProps?.color &&
                    findUpTo(ancestor.parentElement, closestBlock(ancestor), (n) =>
                        hasColor(n, "backgroundColor")
                    )
                ) {
                    return;
                }
            }
            // Over: gradient, applying: anything else => keep
            // Reason: cutting a gradient restarts it on each fragment.
            return false;
        },

        /** Processors */
        normalize_processors: this.normalize.bind(this),
    };

    normalize(root) {
        for (const el of selectElements(root, "font")) {
            if (isRedundantElement(el)) {
                unwrapContents(el);
            }
        }
        return root;
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
                    this.dependencies.format.requestFormat(mode, {
                        applyStyle: false,
                        commit: false,
                    });
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
            if (!color && !element.style.backgroundImage) {
                // A `background` shorthand sets every background longhand, so
                // once the color and the image are cleared the rest lingers as
                // `initial` values.
                const leftovers = [...element.style].filter(
                    (prop) =>
                        prop.startsWith("background-") &&
                        element.style.getPropertyValue(prop) === "initial"
                );
                removeStyle(element, ...leftovers);
            }
        }

        const newClassName = oldClassName
            .replace(mode === "color" ? TEXT_CLASSES_REGEX : BG_CLASSES_REGEX, "")
            .replace(/\btext-gradient\b/g, "") // cannot be combined with setting a background
            .replace(/\s+/, " ");
        if (oldClassName !== newClassName) {
            if (newClassName) {
                element.setAttribute("class", newClassName);
            } else {
                removeClass(element, oldClassName);
            }
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
