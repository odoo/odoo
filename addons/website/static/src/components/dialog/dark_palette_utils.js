import { selectElements } from "@html_editor/utils/dom_traversal";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { convertCSSColorToRgba, convertRgbToHsl } from "@web/core/utils/colors";

/**
 * Keep standard snippets and New Page templates readable with dark palettes.
 * Preview DOM is adapted before it is displayed or inserted into a page.
 */

/**
 * Returns whether the page uses a palette marked as dark.
 *
 * The page document provides the selected palette name. The builder document
 * provides metadata for all available palettes, including the `is-dark` flag.
 *
 * @param {Document} pageDocument
 * @returns {boolean}
 */
export function isDarkColorPalette(pageDocument) {
    if (!pageDocument) {
        return false;
    }
    const paletteName = getCSSVariableValue(
        "color-palettes-name",
        getHtmlStyle(pageDocument)
    ).replace(/'/g, "");
    return (
        getCSSVariableValue(`o-palette-${paletteName}-is-dark`, getHtmlStyle(document)) === "true"
    );
}

/**
 * Adapts standard content to preserve contrast with a dark palette.
 *
 * Standard snippets use `o_cc5` over black filters and `o_cc1` over white
 * filters. Dark palettes require the opposite presets to keep text readable.
 * Custom gradients are considered dark when one visible color stop is dark.
 * Only direct filter children are considered, so a nested section cannot alter
 * the preset of one of its parents.
 *
 * The `carousel-dark` styling is also removed because its dark controls would
 * not be visible on the resulting dark backgrounds.
 *
 * @param {Element} rootEl
 */
export function adaptDarkPaletteContent(rootEl) {
    for (const carouselEl of selectElements(rootEl, ".carousel-dark")) {
        carouselEl.classList.remove("carousel-dark");
    }
    // A standalone snippet can carry its color preset on the root itself.
    const colorPresetEls = selectElements(rootEl, ".o_cc1, .o_cc5");
    for (const colorPresetEl of colorPresetEls) {
        for (const childEl of colorPresetEl.children) {
            if (!childEl.classList.contains("o_we_bg_filter")) {
                continue;
            }
            const classNames = [...childEl.classList];
            // This covers current custom filters, which contain a dark stop.
            const gradientColors = childEl.style.backgroundImage.match(/rgba?\([^)]+\)/g) || [];
            const hasDarkGradient = gradientColors.some((color) => {
                const rgba = convertCSSColorToRgba(color);
                return (
                    rgba &&
                    rgba.opacity > 0 &&
                    convertRgbToHsl(rgba.red, rgba.green, rgba.blue).lightness < 50
                );
            });
            let sourceClass;
            let targetClass;
            if (classNames.some((name) => name.startsWith("bg-black-")) || hasDarkGradient) {
                sourceClass = "o_cc5";
                targetClass = "o_cc1";
            } else if (classNames.some((name) => name.startsWith("bg-white-"))) {
                sourceClass = "o_cc1";
                targetClass = "o_cc5";
            } else {
                continue;
            }
            colorPresetEl.classList.replace(sourceClass, targetClass);
            break;
        }
    }
}
