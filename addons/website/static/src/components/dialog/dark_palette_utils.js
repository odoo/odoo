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
 * @param {Element} rootEl
 */
export function adaptDarkPaletteContent(rootEl) {
    // Launch Countdown uses `o_cc1` and `o-color-5` with dark palettes.
    for (const launchCountdownEl of selectElements(rootEl, ".s_launch_countdown")) {
        launchCountdownEl.classList.replace("o_cc5", "o_cc1");
        const countdownEl = launchCountdownEl.querySelector(".s_countdown");
        if (countdownEl) {
            const color = "o-color-5";
            countdownEl.dataset.textColor = color;
            countdownEl.dataset.progressBarColor = color;
            for (const textEl of countdownEl.querySelectorAll("svg text[fill]")) {
                textEl.setAttribute("fill", `var(--${color})`);
            }
            for (const pathEl of countdownEl.querySelectorAll("svg path[stroke]")) {
                pathEl.setAttribute("stroke", `var(--${color})`);
            }
        }
    }
    // `s_adventure`'s default shape blends into its `bg-white-50` filter with
    // dark palettes. The editor reads the shape data while CSS renders the URL,
    // so update both to keep the color picker in sync.
    for (const adventureEl of selectElements(rootEl, ".s_adventure")) {
        const shapeColor = "o-color-4";
        const shapeData = JSON.parse(adventureEl.dataset.oeShapeData.replace(/'/g, '"'));
        shapeData.colors = { ...shapeData.colors, c5: shapeColor };
        adventureEl.dataset.oeShapeData = JSON.stringify(shapeData);
        const shapeEl = adventureEl.querySelector(":scope > .o_we_shape");
        shapeEl?.style.setProperty(
            "background-image",
            `url("/html_editor/shape/${shapeData.shape}.svg?c5=${shapeColor}")`
        );
    }
    // Dark carousel controls are not visible on dark backgrounds.
    for (const carouselEl of selectElements(rootEl, ".carousel-dark")) {
        carouselEl.classList.remove("carousel-dark");
    }
    // Blurred backgrounds inherit text colors from their closest preset.
    // Dark translucent backgrounds need `o_cc1` to keep text visible.
    for (const backgroundEl of selectElements(rootEl, ".o_bg_blur_option")) {
        const rgba = convertCSSColorToRgba(backgroundEl.style.backgroundColor);
        const isDark =
            rgba &&
            rgba.opacity > 0 &&
            convertRgbToHsl(rgba.red, rgba.green, rgba.blue).lightness < 50;
        const colorPresetEl = backgroundEl.closest(".o_cc");
        if (isDark && colorPresetEl?.classList.contains("o_cc5")) {
            colorPresetEl.classList.replace("o_cc5", "o_cc1");
        }
    }
    // Swap the color preset used over black and white filters. A custom
    // gradient is considered dark when one visible color stop is dark.
    // A standalone snippet can carry its color preset on the root itself.
    const colorPresetEls = selectElements(rootEl, ".o_cc1, .o_cc5");
    for (const colorPresetEl of colorPresetEls) {
        // Only direct filter children can alter their parent's color preset.
        for (const childEl of colorPresetEl.children) {
            if (!childEl.classList.contains("o_we_bg_filter")) {
                continue;
            }
            const classNames = [...childEl.classList];
            const gradientColors = childEl.style.backgroundImage.match(/rgba?\([^)]+\)/g) || [];
            const hasDarkGradient = gradientColors.some((color) => {
                const rgba = convertCSSColorToRgba(color);
                // The 65% threshold keeps text light over all theme gradient
                // filters (e.g. the `s_cover` filter from `theme_monglia`,
                // which contains a color with 61% lightness).
                return (
                    rgba &&
                    rgba.opacity > 0 &&
                    convertRgbToHsl(rgba.red, rgba.green, rgba.blue).lightness < 65
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
            if (colorPresetEl.classList.contains(sourceClass)) {
                colorPresetEl.classList.replace(sourceClass, targetClass);
            }
            break;
        }
    }
}
