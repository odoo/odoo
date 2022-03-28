odoo.define('mass_mailing.snippets.options', function (require) {
"use strict";

const options = require('web_editor.snippets.options');
const {ColorpickerWidget} = require('web.Colorpicker');
const SelectUserValueWidget = options.userValueWidgetsRegistry['we-select'];
const weUtils = require('web_editor.utils');

//--------------------------------------------------------------------------
// Constants
//--------------------------------------------------------------------------

const _getFontName = fontFamily => fontFamily.split(',')[0].replace(/"/g, '').replace(/([a-z])([A-Z])/g, (v, a, b) => `${a} ${b}`).trim();
const _normalizeFontFamily = fontFamily => fontFamily.replace(/"/g, '').replace(/, /g, ',');
const FONT_FAMILIES = [
    'Arial, "Helvetica Neue", Helvetica, sans-serif', // name: "Arial"
    '"Courier New", Courier, "Lucida Sans Typewriter", "Lucida Typewriter", monospace', // name: "Courier New"
    'Georgia, Times, "Times New Roman", serif', // name: "Georgia"
    '"Helvetica Neue", Helvetica, Arial, sans-serif', // name: "Helvetica Neue"
    '"Lucida Grande", "Lucida Sans Unicode", "Lucida Sans", Geneva, Verdana, sans-serif', // name: "Lucida Grande"
    'Tahoma, Verdana, Segoe, sans-serif', // name: "Tahoma"
    'TimesNewRoman, "Times New Roman", Times, Baskerville, Georgia, serif', // name: "Times New Roman"
    '"Trebuchet MS", "Lucida Grande", "Lucida Sans Unicode", "Lucida Sans", Tahoma, sans-serif', // name: "Trebuchet MS"
    'Verdana, Geneva, sans-serif', // name: "Verdana"
].map(fontFamily => _normalizeFontFamily(fontFamily));
const CSS_PREFIX = '.o_mail_wrapper';
const DEFAULT_CSS = `
    ${CSS_PREFIX} h1 {
        font-size: 35px;
        color: #212529;
        font-family: Arial,Helvetica Neue,Helvetica,sans-serif;
    }
    ${CSS_PREFIX} h2 {
        font-size: 28px;
        color: #212529;
        font-family: Arial,Helvetica Neue,Helvetica,sans-serif;
    }
    ${CSS_PREFIX} h3 {
        font-size: 24.5px;
        color: #212529;
        font-family: Arial,Helvetica Neue,Helvetica,sans-serif;
    }
    ${CSS_PREFIX} p {
        font-size: 14px;
        color: #212529;
        font-family: Arial,Helvetica Neue,Helvetica,sans-serif;
    }
    ${CSS_PREFIX} a:not(.btn) {
        text-decoration-line: none;
        color: #276e72
    }
    ${CSS_PREFIX} a[href].btn-primary {
        font-size: 14px;
        color: #FFFFFF;
        background-color: #35979c;
        border-color: #35979c;
        border-style: solid;
        border-width: 1px;
    }
    ${CSS_PREFIX} a[href].btn-secondary {
        font-size: 14px;
        color: #FFFFFF;
        background-color: #685563;
        border-color: #685563;
        border-style: solid;
        border-width: 1px;
    }
    ${CSS_PREFIX} hr {
        border-top-color: #212529;
        border-top-style: solid;
        border-top-width: 1px;
        width: 100%;
    }
`;
const BTN_SIZE_STYLES = {
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
const DEFAULT_BUTTON_SIZE = 'btn-md';
const PRIORITY_STYLES = {
    'h1': ['font-family'],
    'h2': ['font-family'],
    'h3': ['font-family'],
    'p': ['font-family'],
    'a:not(.btn)': [],
    'a[href].btn-primary': [],
    'a[href].btn-secondary': [],
    'hr': [],
};

//--------------------------------------------------------------------------
// Options
//--------------------------------------------------------------------------

// Snippet option for resizing  image and column width inline like excel
options.registry.mass_mailing_sizing_x = options.Class.extend({
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);

        this.containerWidth = this.$target.parent().closest("td, table, div").width();

        var self = this;
        var offset, sib_offset, target_width, sib_width;

        this.$overlay.find(".o_handle.e, .o_handle.w").removeClass("readonly");
        this.isIMG = this.$target.is("img");
        if (this.isIMG) {
            this.$overlay.find(".o_handle.w").addClass("readonly");
        }

        var $body = $(this.ownerDocument.body);
        this.$overlay.find(".o_handle").on('mousedown', function (event) {
            event.preventDefault();
            var $handle = $(this);
            var compass = false;

            _.each(['n', 's', 'e', 'w'], function (handler) {
                if ($handle.hasClass(handler)) { compass = handler; }
            });
            if (self.isIMG) { compass = "image"; }

            $body.on("mousemove.mass_mailing_width_x", function (event) {
                event.preventDefault();
                offset = self.$target.offset().left;
                target_width = self.get_max_width(self.$target);
                if (compass === 'e' && self.$target.next().offset()) {
                    sib_width = self.get_max_width(self.$target.next());
                    sib_offset = self.$target.next().offset().left;
                    self.change_width(event, self.$target, target_width, offset, true);
                    self.change_width(event, self.$target.next(), sib_width, sib_offset, false);
                }
                if (compass === 'w' && self.$target.prev().offset()) {
                    sib_width = self.get_max_width(self.$target.prev());
                    sib_offset = self.$target.prev().offset().left;
                    self.change_width(event, self.$target, target_width, offset, false);
                    self.change_width(event, self.$target.prev(), sib_width, sib_offset, true);
                }
                if (compass === 'image') {
                    self.change_width(event, self.$target, target_width, offset, true);
                }
            });
            $body.one("mouseup", function () {
                $body.off('.mass_mailing_width_x');
            });
        });

        return def;
    },
    change_width: function (event, target, target_width, offset, grow) {
        target.css("width", Math.round(grow ? (event.pageX - offset) : (offset + target_width - event.pageX)));
        this.trigger_up('cover_update');
    },
    get_int_width: function (el) {
        return parseInt($(el).css("width"), 10);
    },
    get_max_width: function ($el) {
        return this.containerWidth - _.reduce(_.map($el.siblings(), this.get_int_width), function (memo, w) { return memo + w; });
    },
    onFocus: function () {
        this._super.apply(this, arguments);

        if (this.$target.is("td, th")) {
            this.$overlay.find(".o_handle.e, .o_handle.w").toggleClass("readonly", this.$target.siblings().length === 0);
        }
    },
});

// Adding compatibility for the outlook compliance of mailings.
// Commit of such compatibility : a14f89c8663c9cafecb1cc26918055e023ecbe42
options.registry.BackgroundImage = options.registry.BackgroundImage.extend({
    start: function () {
        this._super();
        if (this.snippets && this.snippets.split('.')[0] === "mass_mailing") {
            var $table_target = this.$target.find('table:first');
            if ($table_target.length) {
                this.$target = $table_target;
            }
        }
    }
});

options.registry.ImageTools.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getCSSColorValue(color) {
        if (!color || ColorpickerWidget.isCSSColor(color)) {
            return color;
        }
        const doc = this.options.document;
        if (doc && doc.querySelector('.o_mass_mailing_iframe') && !ColorpickerWidget.isCSSColor(color)) {
            const tempEl = doc.body.appendChild(doc.createElement('div'));
            tempEl.className = `bg-${color}`;
            const colorValue = window.getComputedStyle(tempEl).getPropertyValue("background-color").trim();
            tempEl.parentNode.removeChild(tempEl);
            return ColorpickerWidget.normalizeCSSColor(colorValue).replace(/"/g, "'");
        }
        return this._super(...arguments);
    },
});

options.userValueWidgetsRegistry['we-fontfamilypicker'] = SelectUserValueWidget.extend({
    /**
     * @override
     * @see FONT_FAMILIES
     */
    start: async function () {
        const res = await this._super(...arguments);
        // Populate the `we-select` with the font family buttons
        for (const fontFamily of FONT_FAMILIES) {
            const button = document.createElement('we-button');
            button.style.setProperty('font-family', fontFamily);
            button.dataset.customizeCssProperty = fontFamily;
            button.dataset.cssProperty = 'font-family';
            button.dataset.selectorText = this.el.dataset.selectorText;
            button.textContent = _getFontName(fontFamily);
            this.menuEl.appendChild(button);
        };
        return res;
    },
});

options.registry.DesignTab = options.Class.extend({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        // Set the target on the whole editable so apply-to looks within it.
        this.setTarget(this.options.wysiwyg.getEditable());
    },
    /**
     * @override
     */
    async start() {
        const res = await this._super(...arguments);
        const $editable = this.options.wysiwyg.getEditable();
        this.styleElement = $editable[0].ownerDocument.querySelector('#design-element');
        if (!this.styleElement) {
            // If a style element can't be found, create one and initialize it.
            this.styleElement = document.createElement('style');
            this.styleElement.setAttribute('id', 'design-element');
            // The style element needs to be within the layout of the email in
            // order to be saved along with it.
            $editable.find('.o_layout').prepend(this.styleElement);
            this.styleElement.textContent = DEFAULT_CSS;
        }
        // When editing a stylesheet, its content is not updated so it won't be
        // saved along with the mailing. Therefore we need to write its cssText
        // into it. However, when doing that we lose its reference. So we need
        // two separate style elements: one that will be saved and one to hold
        // the stylesheet. Both need to be synchronized, which will be done via
        // `_commitCss`.
        let sheetOwner = $editable[0].ownerDocument.querySelector('#sheet-owner');
        if (!sheetOwner) {
            sheetOwner = document.createElement('style');
            sheetOwner.setAttribute('id', 'sheet-owner');
            $editable[0].ownerDocument.head.appendChild(sheetOwner);
        }
        sheetOwner.disabled = true;
        sheetOwner.textContent = this.styleElement.textContent;
        this.styleSheet = sheetOwner.sheet;
        return res;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Option method to set a css property in the mailing's custom stylesheet.
     * Note: marks all the styles as important to make sure they take precedence
     * on other stylesheets.
     *
     * @param {boolean|string} previewMode
     * @param {string} widgetValue
     * @param {Object} params
     * @param {string} params.selectorText the css selector for which to apply
     *                                     the css
     * @param {string} params.cssProperty the name of the property to edit
     *                                    (camel cased)
     * @param {string} [params.toggle] if 'true', will remove the property if
     *                                 its value is already the one it's being
     *                                 set to
     * @param {string} [params.activeValue] the value to set, if `widgetValue`
     *                                      is not defined.
     * @returns {Promise|undefined}
     */
    customizeCssProperty(previewMode, widgetValue, params) {
        if (!params.selectorText || !params.cssProperty) {
            return;
        }
        let value = widgetValue || params.activeValue;
        if (params.cssProperty.includes('color')) {
            value = weUtils.normalizeColor(value);
        }
        const selectors = this._getSelectors(params.selectorText);
        if (params.cssProperty === 'font-family') {
            // Ensure font-family gets passed to all descendants.
            selectors.push(...selectors.map(selector => selector + ' *'));
        }
        const firstSelector = selectors[0].replace(CSS_PREFIX, '').trim();
        for (const selector of selectors) {
            const priority = PRIORITY_STYLES[firstSelector].includes(params.cssProperty) ? ' !important' : '';
            const rule = this._getRule(selector);
            if (rule) {
                // The rule exists: update it.
                if (params.toggle === 'true' && rule.style.getPropertyValue(params.cssProperty) === value) {
                    rule.style.removeProperty(params.cssProperty);
                } else {
                    // Convert the style to css text and add the new style (the
                    // `style` property is readonly, we can only edit
                    // `cssText`).
                    const cssTexts = [];
                    for (const style of rule.style) {
                        const ownPriority = rule.style.getPropertyPriority(style) ? ' !important' : '';
                        if (style !== params.cssProperty) {
                            cssTexts.push(`${style}: ${rule.style[style]}${priority || ownPriority};`);
                        }
                    }
                    cssTexts.push(`${params.cssProperty}: ${value}${priority};`);
                    rule.style.cssText = cssTexts.join('\n'); // Apply the new css text.
                }
            } else {
                // The rule doesn't exist: create it.
                this.styleSheet.insertRule(`${selector} {
                    ${params.cssProperty}: ${value}${priority};
                }`);
            }
        }
        this._commitCss();
    },
    /**
     * Option method to change the size of buttons.
     *
     * @see BTN_SIZE_STYLES
     * @param {boolean|string} previewMode
     * @param {string} widgetValue ('btn-sm'|'btn-md'|'btn-lg'|''|undefined)
     * @param {Object} params
     * @returns {Promise|undefined}
     */
     applyButtonSize(previewMode, widgetValue, params) {
        for (const [styleName, styleValue] of Object.entries(BTN_SIZE_STYLES[widgetValue || params.activeValue || DEFAULT_BUTTON_SIZE])) {
            if (styleValue) {
                this.customizeCssProperty(previewMode, styleValue, Object.assign({}, params, { cssProperty: styleName }));
            } else {
                // If the value is falsy, remove the property.
                for (const selector of this._getSelectors(params.selectorText)) {
                    const rule = this._getRule(selector);
                    if (rule) {
                        rule.style.removeProperty(styleName);
                    }
                }
            }
        }
        this._commitCss();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Apply the stylesheet's css text to the style element that will be saved.
     */
    _commitCss() {
        const cssTexts = [];
        for (const rule of this.styleSheet.cssRules || this.styleSheet.rules) {
            cssTexts.push(rule.cssText);
        }
        this.styleElement.textContent = cssTexts.join('\n');
    },
    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        const res = await this._super(...arguments);
        if (res === undefined) {
            switch (methodName) {
                case 'customizeCssProperty': {
                    if (!params.selectorText) {
                        return;
                    }
                    const rule = this._getRule(this._getSelectors(params.selectorText)[0]);
                    if (params.possibleValues && params.possibleValues[1] === FONT_FAMILIES[0]) {
                        // For font-family, we need to normalize it so it
                        // matches an option value.
                        return rule && _normalizeFontFamily(rule.style.getPropertyValue('font-family'));
                    } else {
                        return rule && rule.style.getPropertyValue(params.cssProperty);
                    }
                }
                case 'applyButtonSize':
                    // Match a button size by its padding value.
                    const rule = this._getRule(this._getSelectors(params.selectorText)[0]);
                    if (rule) {
                        const classIndex = Object.values(BTN_SIZE_STYLES).findIndex(style => style.padding === rule.style.padding);
                        return classIndex >= 0 ? Object.keys(BTN_SIZE_STYLES)[classIndex] : DEFAULT_BUTTON_SIZE;
                    } else {
                        return DEFAULT_BUTTON_SIZE;
                    }
            }
        } else {
            return res;
        }
    },
    /**
     * Take a CSS selector and split it into separate selectors, all prefixed
     * with the `CSS_PREFIX`. Return them as an array.
     *
     * @see CSS_PREFIX
     * @param {string} selectorText
     * @returns {string[]}
     */
    _getSelectors(selectorText) {
        return selectorText.split(',').map(t => `${t.startsWith(CSS_PREFIX) ? '' : CSS_PREFIX + ' '}${t.trim()}`.trim());;
    },
    /**
     * Take a CSS selector and find its matching rule in the mailing's custom
     * stylesheet, if it exists.
     *
     * @param {string} selectorText
     * @returns {CSSStyleRule|undefined}
     */
    _getRule(selectorText) {
        return [...(this.styleSheet.cssRules || this.styleSheet.rules)].find(rule => rule.selectorText === selectorText);
    },
});

});
