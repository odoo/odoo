import { EDITOR_COLOR_CSS_VARIABLES, isColorCombinationName } from "@html_editor/utils/color";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { backgroundImageCssToParts, getBgImageURLFromURL } from "@html_editor/utils/image";
import { normalizeCSSColor, isCSSColor, isColorGradient, rgbaToHex } from "@web/core/utils/colors";
import { convertNumericToUnit, getCSSVariableValue } from "@html_editor/utils/formatting";

/**
 * window.getComputedStyle cannot work properly with CSS shortcuts (like
 * 'border-width' which is a shortcut for the top + right + bottom + left border
 * widths. If an option wants to customize such a shortcut, it should be listed
 * here with the non-shortcuts property it stands for, in order.
 *
 * @type {Object<string[]>}
 */
export const CSS_SHORTHANDS = {
    "border-width": [
        "border-top-width",
        "border-right-width",
        "border-bottom-width",
        "border-left-width",
    ],
    "border-radius": [
        "border-top-left-radius",
        "border-top-right-radius",
        "border-bottom-right-radius",
        "border-bottom-left-radius",
    ],
    "--box-border-width": [
        "--box-border-top-width",
        "--box-border-right-width",
        "--box-border-bottom-width",
        "--box-border-left-width",
    ],
    "--box-border-radius": [
        "--box-border-top-left-radius",
        "--box-border-top-right-radius",
        "--box-border-bottom-right-radius",
        "--box-border-bottom-left-radius",
    ],
    "border-color": [
        "border-top-color",
        "border-right-color",
        "border-bottom-color",
        "border-left-color",
    ],
    "border-style": [
        "border-top-style",
        "border-right-style",
        "border-bottom-style",
        "border-left-style",
    ],
    padding: ["padding-top", "padding-right", "padding-bottom", "padding-left"],
};
/**
 * Set of all the data attributes relative to the background images.
 */
const BACKGROUND_IMAGE_ATTRIBUTES = new Set([
    "originalId",
    "originalSrc",
    "mimetype",
    "resizeWidth",
    "glFilter",
    "quality",
    "filterOptions",
    "mimetypeBeforeConversion",
]);

/**
 * Converts the given (value + unit) string to a numeric value expressed in
 * the other given css unit.
 *
 * e.g. fct('400ms', 's') -> 0.4
 *
 * @param {string} value
 * @param {string} unitTo
 * @param {string} [cssProp] - the css property on which the unit applies
 * @returns {number}
 */
export function convertValueToUnit(value, unitTo, htmlStyle) {
    const m = getNumericAndUnit(value);
    if (!m) {
        return NaN;
    }
    const numValue = parseFloat(m[0]);
    const valueUnit = m[1];
    return convertNumericToUnit(numValue, valueUnit, unitTo, htmlStyle);
}
/**
 * Returns the numeric value and unit of a css value.
 *
 * e.g. fct('400ms') -> [400, 'ms']
 *
 * @param {string} value
 * @returns {Array|null}
 */
export function getNumericAndUnit(value) {
    const m = value.trim().match(/^(-?[0-9.]+(?:e[+|-]?[0-9]+)?)\s*([^\s]*)$/);
    if (!m) {
        return null;
    }
    return [m[1].trim(), m[2].trim()];
}
/**
 * Checks if two css values are equal.
 *
 * @param {string} value1
 * @param {string} value2
 * @param {string} cssProp - the css property on which the unit applies
 * @param {CSSStyleDeclaration} htmlStyle
 * @returns {boolean}
 */
export function areCssValuesEqual(value1, value2, cssProp, htmlStyle) {
    // String comparison first
    if (value1 === value2) {
        return true;
    }

    // In case the values are a size, they might be made of two parts.
    // TODO this seems completely arbitrary to rely on the presence of '-size'
    // to do this: should not we just list the right CSS property explicitly
    // if we want to do this? That would have avoided the CSS variable fix that
    // had to be made here (the '--' part).
    if (cssProp && cssProp.endsWith("-size") && !cssProp.startsWith("--")) {
        // Avoid re-splitting each part during their individual comparison.
        const pseudoPartProp = cssProp + "-part";
        const re = /-?[0-9.]+(?:e[+|-]?[0-9]+)?\s*[A-Za-z%-]+|auto/g;
        const parts1 = value1.match(re);
        const parts2 = value2.match(re);
        for (const index of [0, 1]) {
            const part1 = parts1 && parts1.length > index ? parts1[index] : "auto";
            const part2 = parts2 && parts2.length > index ? parts2[index] : "auto";
            if (!areCssValuesEqual(part1, part2, pseudoPartProp, htmlStyle)) {
                return false;
            }
        }
        return true;
    }

    // It could be a CSS variable, in that case the actual value has to be
    // retrieved before comparing.
    if (isCSSVariable(value1)) {
        value1 = getCSSVariableValue(value1.substring(6, value1.length - 1), htmlStyle);
    }
    if (isCSSVariable(value2)) {
        value2 = getCSSVariableValue(value2.substring(6, value2.length - 1), htmlStyle);
    }
    if (value1 === value2) {
        return true;
    }

    // They may be colors, normalize then re-compare the resulting string
    const color1 = normalizeCSSColor(value1);
    const color2 = normalizeCSSColor(value2);
    if (color1 === color2) {
        return true;
    }

    // They may be gradients
    const value1IsGradient = isColorGradient(value1);
    const value2IsGradient = isColorGradient(value2);
    if (value1IsGradient !== value2IsGradient) {
        return false;
    }
    if (value1IsGradient) {
        // Kinda hacky and probably inneficient but probably the easiest way:
        // applied the value as background-image of two fakes elements and
        // compare their computed value.
        const temp1El = document.createElement("div");
        temp1El.style.backgroundImage = value1;
        document.body.appendChild(temp1El);
        value1 = getComputedStyle(temp1El).backgroundImage;
        document.body.removeChild(temp1El);

        const temp2El = document.createElement("div");
        temp2El.style.backgroundImage = value2;
        document.body.appendChild(temp2El);
        value2 = getComputedStyle(temp2El).backgroundImage;
        document.body.removeChild(temp2El);

        return value1 === value2;
    }

    // In case the values are meant as box-shadow, this is difficult to compare.
    // In this case we use the kinda hacky and probably inneficient but probably
    // easiest way: applying the value as box-shadow of two fakes elements and
    // compare their computed value.
    if (cssProp === "box-shadow") {
        const temp1El = document.createElement("div");
        temp1El.style.boxShadow = value1;
        document.body.appendChild(temp1El);
        value1 = getComputedStyle(temp1El).boxShadow;
        document.body.removeChild(temp1El);

        const temp2El = document.createElement("div");
        temp2El.style.boxShadow = value2;
        document.body.appendChild(temp2El);
        value2 = getComputedStyle(temp2El).boxShadow;
        document.body.removeChild(temp2El);

        return value1 === value2;
    }

    // Convert the second value in the unit of the first one and compare
    // floating values
    const data = getNumericAndUnit(value1);
    if (!data) {
        return false;
    }
    const numValue1 = data[0];
    const numValue2 = convertValueToUnit(value2, data[1], htmlStyle);
    return Math.abs(numValue1 - numValue2) < Number.EPSILON;
}
/**
 * @param {string} value
 * @returns {boolean}
 */
export function isCSSVariable(value) {
    value = value.replace(/^'|'$/g, "");
    return /^var\(--.+?\)$/.test(value);
}
/**
 * @param {string[]} colorNames
 * @param {string} [prefix='bg-']
 * @returns {string[]}
 */
export function computeColorClasses(colorNames, prefix = "bg-") {
    let hasCCClasses = false;
    const isBgPrefix = prefix === "bg-";
    const classes = colorNames.map((c) => {
        if (isBgPrefix && isColorCombinationName(c)) {
            hasCCClasses = true;
            return `o_cc${c}`;
        }
        return prefix + c;
    });
    if (hasCCClasses) {
        classes.push("o_cc");
    }
    return classes;
}
/**
 * Normalize a color in case it is a variable name so it can be used outside of
 * css.
 *
 * @param {string} color the color to normalize into a css value
 * @returns {string} the normalized color
 */
export function normalizeColor(color, htmlStyle) {
    if (isCSSColor(color)) {
        return color;
    }
    return getCSSVariableValue(color, htmlStyle);
}
/**
 * Parse an element's background-image's url.
 *
 * @param {HTMLElement} el
 * @returns {string|false} the src of the image or false if not parsable
 */
export function getBgImageURLFromEl(el) {
    const style = el.ownerDocument.defaultView.getComputedStyle(el);
    const parts = backgroundImageCssToParts(style.backgroundImage);
    const string = parts.url || "";
    return getBgImageURLFromURL(string);
}
/**
 * Generates a string ID.
 *
 * @private
 * @returns {string}
 */
export function generateHTMLId() {
    return `o${Math.random().toString(36).substring(2, 15)}`;
}
/**
 * Returns the class of the element that matches the specified prefix.
 *
 * @private
 * @param {Element} el element from which to recover the color class
 * @param {string[]} colorNames
 * @param {string} prefix prefix of the color class to recover
 * @returns {string} color class matching the prefix or an empty string
 */
export function getColorClass(el, colorNames, prefix) {
    const prefixedColorNames = computeColorClasses(colorNames, prefix);
    return el.classList.value
        .split(" ")
        .filter((cl) => prefixedColorNames.includes(cl))
        .join(" ");
}
/**
 * Add one or more new attributes related to background images in the
 * BACKGROUND_IMAGE_ATTRIBUTES set.
 *
 * @param {...string} newAttributes The new attributes to add in the
 * BACKGROUND_IMAGE_ATTRIBUTES set.
 */
export function addBackgroundImageAttributes(...newAttributes) {
    BACKGROUND_IMAGE_ATTRIBUTES.add(...newAttributes);
}
/**
 * Check if an attribute is in the BACKGROUND_IMAGE_ATTRIBUTES set.
 *
 * @param {string} attribute The attribute that has to be checked.
 */
export function isBackgroundImageAttribute(attribute) {
    return BACKGROUND_IMAGE_ATTRIBUTES.has(attribute);
}
/**
 * Checks if an element supposedly marked with the o_editable_media class should
 * in fact be editable (checks if its environment looks like a non editable
 * environment whose media should be editable).
 *
 * TODO: the name of this function is voluntarily bad to reflect the fact that
 * this system should be improved. The combination of o_not_editable,
 * o_editable, getContentEditableAreas, getReadOnlyAreas and other concepts
 * related to what should be editable or not should be reviewed.
 *
 * @returns {boolean}
 */
export function shouldEditableMediaBeEditable(mediaEl) {
    // Some sections of the DOM are contenteditable="false" (for
    // example with the help of the o_not_editable class) but have
    // inner media that should be editable (the fact the container
    // is not is to prevent adding text in between those medias).
    // This case is complex and the solution to support it is not
    // perfect: we mark those media with a class and check that they
    // are descendant of a savable.
    return mediaEl.parentElement && mediaEl.parentElement.closest(".o_editable");
}
/**
 * Returns the label of a link element.
 *
 * @param {HTMLElement} linkEl
 * @returns {string}
 */
export function getLinkLabel(linkEl) {
    return linkEl.textContent.replaceAll("\u200B", "").replaceAll("\uFEFF", "");
}
/**
 * Forwards an image source to its carousel thumbnail.
 * @param {HTMLElement} imgEl
 */
export function forwardToThumbnail(imgEl) {
    const carouselEl = imgEl.closest(".carousel");
    if (carouselEl) {
        const carouselInnerEl = imgEl.closest(".carousel-inner");
        const carouselItemEl = imgEl.closest(".carousel-item");
        if (carouselInnerEl && carouselItemEl) {
            const imageIndex = [...carouselInnerEl.children].indexOf(carouselItemEl);
            const miniatureEl = carouselEl.querySelector(
                `.carousel-indicators [data-bs-slide-to="${imageIndex}"]`
            );
            if (miniatureEl && miniatureEl.style.backgroundImage) {
                miniatureEl.style.backgroundImage = `url(${imgEl.getAttribute("src")})`;
            }
        }
    }
}

/**
 * @param {HTMLImageElement} img
 * @returns {Promise<Boolean>}
 */
export async function isImageCorsProtected(img) {
    const src = img.getAttribute("src");
    if (!src) {
        return false;
    }
    let isCorsProtected = false;
    if (!src.startsWith("/") || /\/web\/image\/\d+-redirect\//.test(src)) {
        // The `fetch()` used later in the code might fail if the image is
        // CORS protected. We check upfront if it's the case.
        // Two possible cases:
        // 1. the `src` is an absolute URL from another domain.
        //    For instance, abc.odoo.com vs abc.com which are actually the
        //    same database behind.
        // 2. A "attachment-url" which is just a redirect to the real image
        //    which could be hosted on another website.
        isCorsProtected = await fetch(src, { method: "HEAD" })
            .then(() => false)
            .catch(() => true);
    }
    return isCorsProtected;
}

/**
 * Applies only the needed CSS in the style attribute:
 * - no attribute if value is already the wanted one (possibly from a class)
 * - plain attribute if that change is sufficient to make it applied
 * - important attribute if the plain one did not work
 *
 * @param {HTMLElement} el
 * @param {string} cssProp
 * @param {string} cssValue
 * @param {CSSStyleDeclaration} computedStyle of el
 * @param {boolean} force to always apply as important
 * @param {boolean} allowImportant to avoid applying the style as important
 * @returns {boolean} if a value was applied
 */
export function applyNeededCss(
    el,
    cssProp,
    cssValue,
    computedStyle = el.ownerDocument.defaultView.getComputedStyle(el),
    { force = false, allowImportant = true } = {}
) {
    if (force) {
        el.style.setProperty(cssProp, cssValue, allowImportant ? "important" : "");
        return true;
    }
    el.style.removeProperty(cssProp);
    if (
        !areCssValuesEqual(
            computedStyle.getPropertyValue(cssProp),
            cssValue,
            cssProp,
            computedStyle
        )
    ) {
        el.style.setProperty(cssProp, cssValue);
        // If change had no effect then make it important.
        if (
            allowImportant &&
            !areCssValuesEqual(
                computedStyle.getPropertyValue(cssProp),
                cssValue,
                cssProp,
                computedStyle
            )
        ) {
            el.style.setProperty(cssProp, cssValue, "important");
        }
        return true;
    }
    return false;
}

const builderStylesheet = new CSSStyleSheet();
export function setBuilderCSSVariables(htmlStyle) {
    const styles = [];
    for (const style of EDITOR_COLOR_CSS_VARIABLES) {
        let value = getCSSVariableValue(style, htmlStyle);
        if (value.startsWith("'") && value.endsWith("'")) {
            // Gradient values are recovered within a string.
            value = value.substring(1, value.length - 1);
        }
        styles.push(`--hb-cp-${style}: ${value};`);
    }
    builderStylesheet.replaceSync(`html { ${styles.join(" ")} }`);
    if (!window.top.document.adoptedStyleSheets.find((style) => style === builderStylesheet)) {
        window.top.document.adoptedStyleSheets.push(builderStylesheet);
    }
}

export function parseBoxShadow(value) {
    const regex =
        /(?<color>(rgb(a)?\([^)]*\))|(var\([^)]+\)))\s+(?<offsetX>-?\d+\.?\d*px)\s+(?<offsetY>-?\d+\.?\d*px)\s+(?<blur>-?\d+\.?\d*px)\s+(?<spread>-?\d+\.?\d*px)(?:\s+(?<mode>\w+))?/;
    return value.match(regex)?.groups ?? {};
}

export function getAllUsedColors(el) {
    const usedCustomColors = new Set();
    const collectColor = (colorValue) => {
        if (isCSSColor(colorValue)) {
            usedCustomColors.add(rgbaToHex(colorValue));
        }
    };
    for (const coloredEl of selectElements(el, '[style*="color"]')) {
        for (const colorProperty of ["color", "background-color", "border-color"]) {
            collectColor(coloredEl.style[colorProperty]);
        }
    }
    for (const shadowEl of selectElements(el, '[style*="box-shadow"]')) {
        const shadowValue = shadowEl.style["box-shadow"];
        if (shadowValue) {
            collectColor(parseBoxShadow(shadowValue).color);
        }
    }
    // Find data-*color attributes.
    for (const dataColoredEl of selectElements(el, "*")) {
        for (const attributeName of Object.keys(dataColoredEl.dataset)) {
            if (attributeName.endsWith("olor")) {
                collectColor(dataColoredEl.dataset[attributeName]);
            }
        }
    }
    // Shapes & illustrations.
    const collectUrlColors = (urlString) => {
        const url = new URL(urlString, window.location);
        for (const colorKey of [...url.searchParams.keys()].filter((key) => /c\d/.test(key))) {
            collectColor(url.searchParams.get(colorKey));
        }
    };
    for (const imgEl of selectElements(
        el,
        'img[src^="/html_editor/shape/"], img[src^="/web_editor/shape/"]'
    )) {
        collectUrlColors(imgEl.src);
    }
    for (const bgEl of selectElements(
        el,
        `[style*="background-image: url(\\"/html_editor/shape/"], [style*="background-image: url(\\"/web_editor/shape/"]`
    )) {
        collectUrlColors(getBgImageURLFromEl(bgEl));
    }
    return usedCustomColors;
}
