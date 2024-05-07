/** @odoo-module **/

import {SIZES, MEDIAS_BREAKPOINTS} from "@web/core/ui/ui_service";
import {
    normalizeCSSColor,
    isCSSColor,
} from '@web/core/utils/colors';

let editableWindow = window;
const _setEditableWindow = (ew) => editableWindow = ew;
let editableDocument = document;
const _setEditableDocument = (ed) => editableDocument = ed;

const COLOR_PALETTE_COMPATIBILITY_COLOR_NAMES = ['primary', 'secondary', 'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'success', 'info', 'warning', 'danger'];

/**
 * These constants are colors that can be edited by the user when using
 * web_editor in a website context. We keep track of them so that color
 * palettes and their preview elements can always have the right colors
 * displayed even if website has redefined the colors during an editing
 * session.
 *
 * @type {string[]}
 */
const EDITOR_COLOR_CSS_VARIABLES = [...COLOR_PALETTE_COMPATIBILITY_COLOR_NAMES];
// o-cc and o-colors
for (let i = 1; i <= 5; i++) {
    EDITOR_COLOR_CSS_VARIABLES.push(`o-color-${i}`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-bg`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-headings`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-text`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-primary`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-primary-text`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-secondary`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-secondary-text`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-primary-border`);
    EDITOR_COLOR_CSS_VARIABLES.push(`o-cc${i}-btn-secondary-border`);
}
// Grays
for (let i = 100; i <= 900; i += 100) {
    EDITOR_COLOR_CSS_VARIABLES.push(`${i}`);
}
/**
 * window.getComputedStyle cannot work properly with CSS shortcuts (like
 * 'border-width' which is a shortcut for the top + right + bottom + left border
 * widths. If an option wants to customize such a shortcut, it should be listed
 * here with the non-shortcuts property it stands for, in order.
 *
 * @type {Object<string[]>}
 */
const CSS_SHORTHANDS = {
    'border-width': ['border-top-width', 'border-right-width', 'border-bottom-width', 'border-left-width'],
    'border-radius': ['border-top-left-radius', 'border-top-right-radius', 'border-bottom-right-radius', 'border-bottom-left-radius'],
    'border-color': ['border-top-color', 'border-right-color', 'border-bottom-color', 'border-left-color'],
    'border-style': ['border-top-style', 'border-right-style', 'border-bottom-style', 'border-left-style'],
    'padding': ['padding-top', 'padding-right', 'padding-bottom', 'padding-left'],
};
/**
 * Key-value mapping to list converters from an unit A to an unit B.
 * - The key is a string in the format '$1-$2' where $1 is the CSS symbol of
 *   unit A and $2 is the CSS symbol of unit B.
 * - The value is a function that converts the received value (expressed in
 *   unit A) to another value expressed in unit B. Two other parameters is
 *   received: the css property on which the unit applies and the jQuery element
 *   on which that css property may change.
 */
const CSS_UNITS_CONVERSION = {
    's-ms': () => 1000,
    'ms-s': () => 0.001,
    'rem-px': () => _computePxByRem(),
    'px-rem': () => _computePxByRem(true),
    '%-px': () => -1, // Not implemented but should simply be ignored for now
    'px-%': () => -1, // Not implemented but should simply be ignored for now
};
/**
 * Colors of the default palette, used for substitution in shapes/illustrations.
 * key: number of the color in the palette (ie, o-color-<1-5>)
 * value: color hex code
 */
const DEFAULT_PALETTE = {
    '1': '#3AADAA',
    '2': '#7C6576',
    '3': '#F6F6F6',
    '4': '#FFFFFF',
    '5': '#383E45',
};
/**
 * Set of all the data attributes relative to the background images.
 */
const BACKGROUND_IMAGE_ATTRIBUTES = new Set([
    "originalId", "originalSrc", "mimetype", "resizeWidth", "glFilter", "quality", "bgSrc",
    "filterOptions",
    "mimetypeBeforeConversion",
]);

/**
 * Computes the number of "px" needed to make a "rem" unit. Subsequent calls
 * returns the cached computed value.
 *
 * @param {boolean} [toRem=false]
 * @returns {float} - number of px by rem if 'toRem' is false
 *                  - the inverse otherwise
 */
function _computePxByRem(toRem) {
    if (editableDocument.PX_BY_REM === undefined) {
        const htmlStyle = editableWindow.getComputedStyle(editableDocument.documentElement);
        editableDocument.PX_BY_REM = parseFloat(htmlStyle['font-size']);
    }
    return toRem ? (1 / editableDocument.PX_BY_REM) : editableDocument.PX_BY_REM;
}
/**
 * Converts the given (value + unit) string to a numeric value expressed in
 * the other given css unit.
 *
 * e.g. fct('400ms', 's') -> 0.4
 *
 * @param {string} value
 * @param {string} unitTo
 * @param {string} [cssProp] - the css property on which the unit applies
 * @param {jQuery} [$target] - the jQuery element on which that css property
 *                             may change
 * @returns {number}
 */
function _convertValueToUnit(value, unitTo, cssProp, $target) {
    const m = _getNumericAndUnit(value);
    if (!m) {
        return NaN;
    }
    const numValue = parseFloat(m[0]);
    const valueUnit = m[1];
    return _convertNumericToUnit(numValue, valueUnit, unitTo, cssProp, $target);
}
/**
 * Converts the given numeric value expressed in the given css unit into
 * the corresponding numeric value expressed in the other given css unit.
 *
 * e.g. fct(400, 'ms', 's') -> 0.4
 *
 * @param {number} value
 * @param {string} unitFrom
 * @param {string} unitTo
 * @param {string} [cssProp] - the css property on which the unit applies
 * @param {jQuery} [$target] - the jQuery element on which that css property
 *                             may change
 * @returns {number}
 */
function _convertNumericToUnit(value, unitFrom, unitTo, cssProp, $target) {
    if (Math.abs(value) < Number.EPSILON || unitFrom === unitTo) {
        return value;
    }
    const converter = CSS_UNITS_CONVERSION[`${unitFrom}-${unitTo}`];
    if (converter === undefined) {
        throw new Error(`Cannot convert '${unitFrom}' units into '${unitTo}' units !`);
    }
    return value * converter(cssProp, $target);
}
/**
 * Returns the numeric value and unit of a css value.
 *
 * e.g. fct('400ms') -> [400, 'ms']
 *
 * @param {string} value
 * @returns {Array|null}
 */
function _getNumericAndUnit(value) {
    const m = value.trim().match(/^(-?[0-9.]+(?:e[+|-]?[0-9]+)?)\s*([A-Za-z%-]*)$/);
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
 * @param {string} [cssProp] - the css property on which the unit applies
 * @param {jQuery} [$target] - the jQuery element on which that css property
 *                             may change
 * @returns {boolean}
 */
function _areCssValuesEqual(value1, value2, cssProp, $target) {
    // String comparison first
    if (value1 === value2) {
        return true;
    }

    // In case the values are a size, they might be made of two parts.
    if (cssProp && cssProp.endsWith('-size')) {
        // Avoid re-splitting each part during their individual comparison.
        const pseudoPartProp = cssProp + '-part';
        const re = /-?[0-9.]+(?:e[+|-]?[0-9]+)?\s*[A-Za-z%-]+|auto/g;
        const parts1 = value1.match(re);
        const parts2 = value2.match(re);
        for (const index of [0, 1]) {
            const part1 = parts1 && parts1.length > index ? parts1[index] : 'auto';
            const part2 = parts2 && parts2.length > index ? parts2[index] : 'auto';
            if (!_areCssValuesEqual(part1, part2, pseudoPartProp, $target)) {
                return false;
            }
        }
        return true;
    }

    // It could be a CSS variable, in that case the actual value has to be
    // retrieved before comparing.
    if (value1.startsWith('var(--')) {
        value1 = _getCSSVariableValue(value1.substring(6, value1.length - 1));
    }
    if (value2.startsWith('var(--')) {
        value2 = _getCSSVariableValue(value2.substring(6, value2.length - 1));
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
    const value1IsGradient = _isColorGradient(value1);
    const value2IsGradient = _isColorGradient(value2);
    if (value1IsGradient !== value2IsGradient) {
        return false;
    }
    if (value1IsGradient) {
        // Kinda hacky and probably inneficient but probably the easiest way:
        // applied the value as background-image of two fakes elements and
        // compare their computed value.
        const temp1El = document.createElement('div');
        temp1El.style.backgroundImage = value1;
        document.body.appendChild(temp1El);
        value1 = getComputedStyle(temp1El).backgroundImage;
        document.body.removeChild(temp1El);

        const temp2El = document.createElement('div');
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
    if (cssProp === 'box-shadow') {
        const temp1El = document.createElement('div');
        temp1El.style.boxShadow = value1;
        document.body.appendChild(temp1El);
        value1 = getComputedStyle(temp1El).boxShadow;
        document.body.removeChild(temp1El);

        const temp2El = document.createElement('div');
        temp2El.style.boxShadow = value2;
        document.body.appendChild(temp2El);
        value2 = getComputedStyle(temp2El).boxShadow;
        document.body.removeChild(temp2El);

        return value1 === value2;
    }

    // Convert the second value in the unit of the first one and compare
    // floating values
    const data = _getNumericAndUnit(value1);
    if (!data) {
        return false;
    }
    const numValue1 = data[0];
    const numValue2 = _convertValueToUnit(value2, data[1], cssProp, $target);
    return (Math.abs(numValue1 - numValue2) < Number.EPSILON);
}
/**
 * @param {string|number} name
 * @returns {boolean}
 */
function _isColorCombinationName(name) {
    const number = parseInt(name);
    return (!isNaN(number) && number % 100 !== 0);
}
/**
 * @param {string[]} colorNames
 * @param {string} [prefix='bg-']
 * @returns {string[]}
 */
function _computeColorClasses(colorNames, prefix = 'bg-') {
    let hasCCClasses = false;
    const isBgPrefix = (prefix === 'bg-');
    const classes = colorNames.map(c => {
        if (isBgPrefix && _isColorCombinationName(c)) {
            hasCCClasses = true;
            return `o_cc${c}`;
        }
        return (prefix + c);
    });
    if (hasCCClasses) {
        classes.push('o_cc');
    }
    return classes;
}
/**
 * @param {string} key
 * @param {CSSStyleDeclaration} [htmlStyle] if not provided, it is computed
 * @returns {string}
 */
function _getCSSVariableValue(key, htmlStyle) {
    if (htmlStyle === undefined) {
        htmlStyle = editableWindow.getComputedStyle(editableWindow.document.documentElement);
    }
    // Get trimmed value from the HTML element
    let value = htmlStyle.getPropertyValue(`--${key}`).trim();
    // If it is a color value, it needs to be normalized
    value = normalizeCSSColor(value);
    // Normally scss-string values are "printed" single-quoted. That way no
    // magic conversation is needed when customizing a variable: either save it
    // quoted for strings or non quoted for colors, numbers, etc. However,
    // Chrome has the annoying behavior of changing the single-quotes to
    // double-quotes when reading them through getPropertyValue...
    return value.replace(/"/g, "'");
}
/**
 * Normalize a color in case it is a variable name so it can be used outside of
 * css.
 *
 * @param {string} color the color to normalize into a css value
 * @returns {string} the normalized color
 */
function _normalizeColor(color) {
    if (isCSSColor(color)) {
        return color;
    }
    return _getCSSVariableValue(color);
}
/**
 * Parse an element's background-image's url.
 *
 * @param {string} string a css value in the form 'url("...")'
 * @returns {string|false} the src of the image or false if not parsable
 */
function _getBgImageURL(el) {
    const parts = _backgroundImageCssToParts($(el).css('background-image'));
    const string = parts.url || '';
    const match = string.match(/^url\((['"])(.*?)\1\)$/);
    if (!match) {
        return '';
    }
    const matchedURL = match[2];
    // Make URL relative if possible
    const fullURL = new URL(matchedURL, window.location.origin);
    if (fullURL.origin === window.location.origin) {
        return fullURL.href.slice(fullURL.origin.length);
    }
    return matchedURL;
}
/**
 * Extracts url and gradient parts from the background-image CSS property.
 *
 * @param {string} CSS 'background-image' property value
 * @returns {Object} contains the separated 'url' and 'gradient' parts
 */
function _backgroundImageCssToParts(css) {
    const parts = {};
    css = css || '';
    if (css.startsWith('url(')) {
        const urlEnd = css.indexOf(')') + 1;
        parts.url = css.substring(0, urlEnd).trim();
        const commaPos = css.indexOf(',', urlEnd);
        css = commaPos > 0 ? css.substring(commaPos + 1) : '';
    }
    if (_isColorGradient(css)) {
        parts.gradient = css.trim();
    }
    return parts;
}
/**
 * Combines url and gradient parts into a background-image CSS property value
 *
 * @param {Object} contains the separated 'url' and 'gradient' parts
 * @returns {string} CSS 'background-image' property value
 */
function _backgroundImagePartsToCss(parts) {
    let css = parts.url || '';
    if (parts.gradient) {
        css += (css ? ', ' : '') + parts.gradient;
    }
    return css || 'none';
}
/**
 * @param {string} [value]
 * @returns {boolean}
 */
function _isColorGradient(value) {
    // FIXME duplicated in odoo-editor/utils.js
    return value && value.includes('-gradient(');
}
/**
 * Generates a string ID.
 *
 * @private
 * @returns {string}
 */
function _generateHTMLId() {
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
function _getColorClass(el, colorNames, prefix) {
    const prefixedColorNames = _computeColorClasses(colorNames, prefix);
    return el.classList.value.split(' ').filter(cl => prefixedColorNames.includes(cl)).join(' ');
}
/**
 * Add one or more new attributes related to background images in the
 * BACKGROUND_IMAGE_ATTRIBUTES set.
 *
 * @param {...string} newAttributes The new attributes to add in the
 * BACKGROUND_IMAGE_ATTRIBUTES set.
 */
function _addBackgroundImageAttributes(...newAttributes) {
    BACKGROUND_IMAGE_ATTRIBUTES.add(...newAttributes);
}
/**
 * Check if an attribute is in the BACKGROUND_IMAGE_ATTRIBUTES set.
 *
 * @param {string} attribute The attribute that has to be checked.
 */
function _isBackgroundImageAttribute(attribute) {
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
function _shouldEditableMediaBeEditable(mediaEl) {
    // Some sections of the DOM are contenteditable="false" (for
    // example with the help of the o_not_editable class) but have
    // inner media that should be editable (the fact the container
    // is not is to prevent adding text in between those medias).
    // This case is complex and the solution to support it is not
    // perfect: we mark those media with a class and check that the
    // first non editable ancestor is in fact in an editable parent.
    const parentEl = mediaEl.parentElement;
    const nonEditableAncestorRootEl = parentEl && parentEl.closest('[contenteditable="false"]');
    return nonEditableAncestorRootEl
        && nonEditableAncestorRootEl.parentElement
        && nonEditableAncestorRootEl.parentElement.isContentEditable;
}
/**
 * Checks if the view of the targeted element is mobile.
 *
 * @param {HTMLElement} targetEl - target of the editor
 * @returns {boolean}
 */
function _isMobileView(targetEl) {
    const mobileViewThreshold = MEDIAS_BREAKPOINTS[SIZES.LG].minWidth;
    const clientWidth = targetEl.ownerDocument.defaultView?.frameElement?.clientWidth ||
        targetEl.ownerDocument.documentElement.clientWidth;
    return clientWidth && clientWidth < mobileViewThreshold;
}
/**
 * Returns the label of a link element.
 *
 * @param {HTMLElement} linkEl
 * @returns {string}
 */
function _getLinkLabel(linkEl) {
    return linkEl.textContent.replaceAll("\u200B", "").replaceAll("\uFEFF", "");
}

export default {
    COLOR_PALETTE_COMPATIBILITY_COLOR_NAMES: COLOR_PALETTE_COMPATIBILITY_COLOR_NAMES,
    CSS_SHORTHANDS: CSS_SHORTHANDS,
    CSS_UNITS_CONVERSION: CSS_UNITS_CONVERSION,
    DEFAULT_PALETTE: DEFAULT_PALETTE,
    EDITOR_COLOR_CSS_VARIABLES: EDITOR_COLOR_CSS_VARIABLES,
    computePxByRem: _computePxByRem,
    convertValueToUnit: _convertValueToUnit,
    convertNumericToUnit: _convertNumericToUnit,
    getNumericAndUnit: _getNumericAndUnit,
    areCssValuesEqual: _areCssValuesEqual,
    isColorCombinationName: _isColorCombinationName,
    isColorGradient: _isColorGradient,
    computeColorClasses: _computeColorClasses,
    getCSSVariableValue: _getCSSVariableValue,
    normalizeColor: _normalizeColor,
    getBgImageURL: _getBgImageURL,
    backgroundImageCssToParts: _backgroundImageCssToParts,
    backgroundImagePartsToCss: _backgroundImagePartsToCss,
    generateHTMLId: _generateHTMLId,
    getColorClass: _getColorClass,
    setEditableWindow: _setEditableWindow,
    setEditableDocument: _setEditableDocument,
    addBackgroundImageAttributes: _addBackgroundImageAttributes,
    isBackgroundImageAttribute: _isBackgroundImageAttribute,
    shouldEditableMediaBeEditable: _shouldEditableMediaBeEditable,
    isMobileView: _isMobileView,
    getLinkLabel: _getLinkLabel,
};
