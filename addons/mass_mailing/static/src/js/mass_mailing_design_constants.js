/** @odoo-module alias=mass_mailing.design_constants**/

export const CSS_PREFIX = '.o_mail_wrapper';

export const BTN_SIZE_STYLES = {
    'btn-sm': {
        'padding': '3px 7.5px',
        'font-size': '0.875rem',
        'line-height': '1.5rem',
    },
    'btn-lg': {
        'padding': '7px 14px',
        'font-size': '1.25rem',
        'line-height': '1.5rem',
    },
    'btn-md': {
        'padding': false, // Property must be removed.
        'font-size': '14px',
        'line-height': false, // Property must be removed.
    },
};
export const DEFAULT_BUTTON_SIZE = 'btn-md';
export const PRIORITY_STYLES = {
    'h1': ['font-family'],
    'h2': ['font-family'],
    'h3': ['font-family'],
    'p': ['font-family'],
    'a:not(.btn)': [],
    'a.btn.btn-primary': [],
    'a.btn.btn-secondary': [],
    'hr': ['border-top-width','border-top-style','border-top-color'],
};
export const RE_CSS_TEXT_MATCH = /([^{]+)([^}]+)/;
export const RE_SELECTOR_ENDS_WITH_GT_STAR = />\s*\*\s*$/;

export const transformFontFamilySelector = selector => {
    if (selector.trim().endsWith(':not(.fa)')) {
        return [selector];
    }
    if (!selector.endsWith('*')) {
        return [`${selector.trim()}:not(.fa)`, `${selector.trim()} :not(.fa)`];
    } else if (RE_SELECTOR_ENDS_WITH_GT_STAR.test(selector)) {
        return [`${selector.replace(RE_SELECTOR_ENDS_WITH_GT_STAR, '').trim()} :not(.fa)`];
    }
}
/**
 * Take a css text and splits each comma-separated selector into separate
 * styles, applying the css prefix to each. Return the modified css text.
 *
 * @param {string} [css]
 * @returns {string}
 */
export const splitCss = css => {
    const styleElement = document.createElement('style');
    styleElement.textContent = css;
    // Temporarily insert the style element in the dom to have a stylesheet.
    document.head.appendChild(styleElement);
    const rules = [...styleElement.sheet.cssRules];
    styleElement.remove();
    const stylesToWrite = {};
    for (const rule of rules) {
        const styles = rule.style;
        for (let selector of rule.selectorText.split(',')) {
            if (!selector.trim().startsWith(CSS_PREFIX)) {
                selector = `${CSS_PREFIX} ${selector.trim()}`;
            }
            for (const style of rule.style) {
                let selectors = [selector];
                if (style === 'font-family') {
                    // Ensure font-family gets passed to all descendants and never
                    // overwrite font awesome.
                    selectors = transformFontFamilySelector(selector);
                }
                for (const selectorToWriteTo of selectors) {
                    if (!stylesToWrite[selectorToWriteTo]) {
                        stylesToWrite[selectorToWriteTo] = [];
                    }
                    stylesToWrite[selectorToWriteTo].push([style, styles[style] + (styles.getPropertyPriority(style) === 'important' ? ' !important' : '')]);
                }
            }
        }
    }
    return Object.entries(stylesToWrite).map(([selector, styles]) => (
        `${selector.trim()} {\n${styles.map(([styleName, style]) => `    ${styleName}: ${style};`).join('\n')}\n}`
    )).join('\n');
};
export const getFontName = fontFamily => fontFamily.split(',')[0].replace(/"/g, '').replace(/([a-z])([A-Z])/g, (v, a, b) => `${a} ${b}`).trim();
export const normalizeFontFamily = fontFamily => fontFamily.replace(/"/g, '').replace(/, /g, ',');
export const initializeDesignTabCss = $editable => {
        let styleElement = $editable.get(0).ownerDocument.querySelector('#design-element');
        if (styleElement) {
            styleElement.textContent = splitCss(styleElement.textContent);
        } else {
            // If a style element can't be found, create one and initialize it.
            styleElement = document.createElement('style');
            styleElement.setAttribute('id', 'design-element');
        }
        // The style element needs to be within the layout of the email in
        // order to be saved along with it.
        $editable.find('.o_layout').prepend(styleElement);
};

export const FONT_FAMILIES = [
    'Arial, "Helvetica Neue", Helvetica, sans-serif', // name: "Arial"
    '"Courier New", Courier, "Lucida Sans Typewriter", "Lucida Typewriter", monospace', // name: "Courier New"
    'Georgia, Times, "Times New Roman", serif', // name: "Georgia"
    '"Helvetica Neue", Helvetica, Arial, sans-serif', // name: "Helvetica Neue"
    '"Lucida Grande", "Lucida Sans Unicode", "Lucida Sans", Geneva, Verdana, sans-serif', // name: "Lucida Grande"
    'Tahoma, Verdana, Segoe, sans-serif', // name: "Tahoma"
    'TimesNewRoman, "Times New Roman", Times, Baskerville, Georgia, serif', // name: "Times New Roman"
    '"Trebuchet MS", "Lucida Grande", "Lucida Sans Unicode", "Lucida Sans", Tahoma, sans-serif', // name: "Trebuchet MS"
    'Verdana, Geneva, sans-serif', // name: "Verdana"
].map(fontFamily => normalizeFontFamily(fontFamily));

export default {
    CSS_PREFIX, BTN_SIZE_STYLES, DEFAULT_BUTTON_SIZE, PRIORITY_STYLES,
    RE_CSS_TEXT_MATCH, FONT_FAMILIES, RE_SELECTOR_ENDS_WITH_GT_STAR,
    splitCss, getFontName, normalizeFontFamily, initializeDesignTabCss,
    transformFontFamilySelector,
}
