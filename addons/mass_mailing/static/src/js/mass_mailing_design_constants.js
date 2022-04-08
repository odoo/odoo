/** @odoo-module alias=mass_mailing.design_constants**/

export const CSS_PREFIX = '.o_mail_wrapper';
export const DEFAULT_CSS_OBJECT = {
    h1: {
        'font-size': '35px',
        color: '#212529',
        'font-family': 'Arial,Helvetica Neue,Helvetica,sans-serif',
    },
    h2: {
        'font-size': '28px',
        color: '#212529',
        'font-family': 'Arial,Helvetica Neue,Helvetica,sans-serif',
    },
    h3: {
        'font-size': '24.5px',
        color: '#212529',
        'font-family': 'Arial,Helvetica Neue,Helvetica,sans-serif',
    },
    'p, p > *, li, li > *': {
        'font-size': '14px',
        color: '#212529',
        'font-family': 'Arial,Helvetica Neue,Helvetica,sans-serif',
    },
    'a:not(.btn), a.btn-link': {
        'text-decoration-line': 'none',
        color: '#276e72',
    },
    'a.btn-primary, a.btn-outline-primary, a.btn-fill-primary': {
        'font-size': '12.25px',
        color: '#FFFFFF',
        'background-color': '#35979c',
        'border-color': '#35979c',
        'border-style': 'solid',
        'border-width': '1px',
    },
    'a.btn-secondary, a.btn-outline-secondary, a.btn-fill-secondary': {
        'font-size': '12.25px',
        color: '#FFFFFF',
        'background-color': '#685563',
        'border-color': '#685563',
        'border-style': 'solid',
        'border-width': '1px',
    },
    hr: {
        'border-top-color': '#212529',
        'border-top-style': 'solid',
        'border-top-width': '1px',
        width: '100%',
    }
};
export const DEFAULT_CSS = Object.keys(DEFAULT_CSS_OBJECT).map( // selectors
    key => key.split(',').map( // each individual comma separated selector
        selector => `${CSS_PREFIX} ${selector.trim()} {\n    ${ // selector {
            Object.keys(DEFAULT_CSS_OBJECT[key]).map( // css properties
                prop => `${prop}: ${DEFAULT_CSS_OBJECT[key][prop]}`) // [prop: value]
                    .join(';\n    ')}\n}` // prop: value;
    ).join('\n')
).join('\n'); // css text

export const BTN_SIZE_STYLES = {
    'btn-sm': {
        'padding': '0.25rem 0.5rem',
        'font-size': '0.875rem',
        'line-height': '1.5rem',
    },
    'btn-lg': {
        'padding': '0.5rem 1rem',
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
    'a.btn-primary': [],
    'a.btn-secondary': [],
    'hr': [],
};
export const RE_CSS_TEXT_MATCH = /([^{]+)([^}]+)/;

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
    const result = rules.map(rule => {
        const [, fullSelector, styles] = rule.cssText.match(RE_CSS_TEXT_MATCH);
        return fullSelector.split(',').map(selector => {
            if (!selector.trim().startsWith(CSS_PREFIX)) {
                selector = `${CSS_PREFIX} ${selector.trim()}`;
            }
            return `${selector.trim()} {${styles.replace('{', '').trim()}}`;
        }).join('');
    }).join('');
    return result;
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
            // The style element needs to be within the layout of the email in
            // order to be saved along with it.
            $editable.find('.o_layout').prepend(styleElement);
            styleElement.textContent = splitCss(DEFAULT_CSS);
        }
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
    CSS_PREFIX, DEFAULT_CSS_OBJECT, DEFAULT_CSS, BTN_SIZE_STYLES,
    DEFAULT_BUTTON_SIZE, PRIORITY_STYLES, RE_CSS_TEXT_MATCH, FONT_FAMILIES,
    splitCss, getFontName, normalizeFontFamily, initializeDesignTabCss,
}
