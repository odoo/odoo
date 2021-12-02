odoo.define('wysiwyg.widgets.Link', function (require) {
'use strict';

const core = require('web.core');
const OdooEditorLib = require('@web_editor/../lib/odoo-editor/src/OdooEditor');
const Widget = require('web.Widget');
const {isColorGradient} = require('web_editor.utils');

const getDeepRange = OdooEditorLib.getDeepRange;
const getInSelection = OdooEditorLib.getInSelection;
const _t = core._t;

/**
 * Allows to customize link content and style.
 */
const Link = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    events: {
        'input': '_onAnyChange',
        'change': '_onAnyChange',
        'input input[name="url"]': '_onURLInput',
    },

    /**
     * @constructor
     * @param {Boolean} data.isButton - whether if the target is a button element.
     */
    init: function (parent, options, editable, data, $button, link) {
        this.options = options || {};
        this._super(parent, _.extend({
            title: _t("Link to"),
        }, this.options));

        this._setLinkContent = true;

        this.data = data || {};
        this.isButton = this.data.isButton;
        this.$button = $button;
        this.noFocusUrl = this.options.noFocusUrl;

        this.data.className = this.data.className || "";
        this.data.iniClassName = this.data.iniClassName || "";
        this.needLabel = this.data.needLabel || false;

        // Using explicit type 'link' to preserve style when the target is <button class="...btn-link"/>.
        this.colorsData = [
            {type: this.isButton ? 'link' : '', label: _t("Link"), btnPreview: 'link'},
            {type: 'primary', label: _t("Primary"), btnPreview: 'primary'},
            {type: 'secondary', label: _t("Secondary"), btnPreview: 'secondary'},
            {type: 'custom', label: _t("Custom"), btnPreview: 'custom'},
            // Note: by compatibility the dialog should be able to remove old
            // colors that were suggested like the BS status colors or the
            // alpha -> epsilon classes. This is currently done by removing
            // all btn-* classes anyway.
        ];

        this.editable = editable;
        this.$editable = $(editable);

        if (link) {
            const range = document.createRange();
            range.selectNodeContents(link);
            this.data.range = range;
            this.$link = $(link);
            this.linkEl = link;
        } else {
            const selection = editable && editable.ownerDocument.getSelection();
            this.data.range = selection && selection.rangeCount && selection.getRangeAt(0);
        }

        if (this.data.range) {
            this.$link = this.$link || $(OdooEditorLib.getInSelection(this.editable.ownerDocument, 'a'));
            this.linkEl = this.$link[0];
            this.data.iniClassName = this.$link.attr('class') || '';
            this.colorCombinationClass = false;
            let $node = this.$link;
            while ($node.length && !$node.is('body')) {
                const className = $node.attr('class') || '';
                const m = className.match(/\b(o_cc\d+)\b/g);
                if (m) {
                    this.colorCombinationClass = m[0];
                    break;
                }
                $node = $node.parent();
            }
            const linkNode = this.$link[0] || this.data.range.cloneContents();
            const linkText = linkNode.innerHTML || linkNode.textContent;
            this.data.content = linkText.replace(/[ \t\r\n]+/g, ' ');
            this.data.originalText = this.data.content;
            this.data.url = this.$link.attr('href') || '';
        } else {
            this.data.content = this.data.content ? this.data.content.replace(/[ \t\r\n]+/g, ' ') : '';
        }

        if (!this.data.url) {
            const urls = this.data.content.match(OdooEditorLib.URL_REGEX_WITH_INFOS);
            if (urls) {
                this.data.url = urls[0];
            }
        }

        if (this.linkEl) {
            this.data.isNewWindow = this.data.isNewWindow || this.linkEl.target === '_blank';
        }

        const allBtnColorPrefixes = /(^|\s+)(bg|text|border)(-[a-z0-9_-]*)?/gi;
        const allBtnClassSuffixes = /(^|\s+)btn(?!-block)(-[a-z0-9_-]*)?/gi;
        const allBtnShapes = /\s*(rounded-circle|flat)\s*/gi;
        this.data.className = this.data.iniClassName
            .replace(allBtnColorPrefixes, ' ')
            .replace(allBtnClassSuffixes, ' ')
            .replace(allBtnShapes, ' ');
        // 'o_submit' class will force anchor to be handled as a button in linkdialog.
        if (/(?:s_website_form_send|o_submit)/.test(this.data.className)) {
            this.isButton = true;
        }
    },
    /**
     * @override
     */
    start: function () {
        for (const option of this._getLinkOptions()) {
            const $option = $(option);
            const value = $option.is('input') ? $option.val() : $option.data('value');
            let active = false;
            if (value) {
                const subValues = value.split(',');
                let subActive = true;
                for (let subValue of subValues) {
                    const classPrefix = new RegExp('(^|btn-| |btn-outline-|btn-fill-)' + subValue);
                    subActive = subActive && classPrefix.test(this.data.iniClassName);
                }
                active = subActive;
            } else {
                active = !this.data.iniClassName || this.data.iniClassName.includes('btn-link') || !this.data.iniClassName.includes('btn-');
            }
            this._setSelectOption($option, active);
        }
        if (this.data.url) {
            var match = /mailto:(.+)/.exec(this.data.url);
            this.$('input[name="url"]').val(match ? match[1] : this.data.url);
            this._onURLInput();
        }

        this._updateOptionsUI();

        if (!this.noFocusUrl) {
            this.focusUrl();
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Apply the new link to the DOM (via `this.$link`).
     *
     * @param {object} data
     */
    applyLinkToDom: function (data) {
        // Some mass mailing template use <a class="btn btn-link"> instead of just a simple <a>.
        // And we need to keep the classes because the a.btn.btn-link have some special css rules.
        if (!data.classes.includes('btn') && this.data.iniClassName.includes("btn-link")) {
            data.classes += " btn btn-link";
        }
        if (['btn-custom', 'btn-outline-custom', 'btn-fill-custom'].some(className =>
            data.classes.includes(className)
        )) {
            this.$link.css('color', data.classes.includes(data.customTextColor) ? '' : data.customTextColor);
            this.$link.css('background-color', data.classes.includes(data.customFill) || isColorGradient(data.customFill) ? '' : data.customFill);
            this.$link.css('background-image', isColorGradient(data.customFill) ? data.customFill : '');
            this.$link.css('border-width', data.customBorderWidth);
            this.$link.css('border-style', data.customBorderStyle);
            this.$link.css('border-color', data.customBorder);
        } else {
            this.$link.css('color', '');
            this.$link.css('background-color', '');
            this.$link.css('background-image', '');
            this.$link.css('border-width', '');
            this.$link.css('border-style', '');
            this.$link.css('border-color', '');
        }
        const attrs = Object.assign({}, this.data.oldAttributes, {
            href: data.url,
            target: data.isNewWindow ? '_blank' : '',
        });
        if (data.classes) {
            data.classes = data.classes.replace(/o_default_snippet_text/, '');
            attrs.class = `${data.classes}`;
        }
        if (data.rel) {
            attrs.rel = `${data.rel}`;
        }

        this.$link.attr(attrs);
        if (!this.$link.attr('target')) {
            this.$link[0].removeAttribute('target');
        }
        if (this._setLinkContent && (data.content !== this.data.originalText || data.url !== this.data.url)) {
            const content = (data.content && data.content.length) ? data.content : data.url;
            // If there is a this.data.originalText, it means that we selected
            // the text and we could not change the content through the text
            // input.html() is needed in case we selected rich html content.
            if (this.data.originalText) {
                this.$link.html(content);
            } else {
                this.$link.text(content);
            }
        }
    },
    /**
     * Return the link element to edit. Create one from selection if none was
     * present in selection.
     *
     * @param {Node} editable
     * @returns {Node}
     */
    getOrCreateLink: function (editable) {
        const doc = editable.ownerDocument;
        this.needLabel = this.needLabel || false;
        let link = getInSelection(doc, 'a');
        const $link = $(link);
        const range = getDeepRange(editable, {splitText: true, select: true, correctTripleClick: true});
        if (link && (!$link.has(range.startContainer).length || !$link.has(range.endContainer).length)) {
            // Expand the current link to include the whole selection.
            let before = link.previousSibling;
            while (before !== null && range.intersectsNode(before)) {
                link.insertBefore(before, link.firstChild);
                before = link.previousSibling;
            }
            let after = link.nextSibling;
            while (after !== null && range.intersectsNode(after)) {
                link.appendChild(after);
                after = link.nextSibling;
            }
        } else if (!link) {
            link = document.createElement('a');
            if (range.collapsed) {
                range.insertNode(link);
                this.needLabel = true;
            } else {
                link.appendChild(range.extractContents());
                range.insertNode(link);
            }
        }
        return link;
    },
    /**
     * Focuses the url input.
     */
    focusUrl() {
        const urlInput = this.el.querySelector('input[name="url"]');
        urlInput.focus();
        urlInput.select();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Abstract method: adapt the link to changes.
     *
     * @abstract
     * @private
     */
    _adaptPreview: function () {},
    /**
     * @private
     */
    _correctLink: function (url) {
        if (url.indexOf('mailto:') === 0 || url.indexOf('tel:') === 0) {
            url = url.replace(/^tel:([0-9]+)$/, 'tel://$1');
        } else if (url.indexOf('@') !== -1 && url.indexOf(':') === -1) {
            url = 'mailto:' + url;
        } else if (url.indexOf('://') === -1 && url[0] !== '/'
                    && url[0] !== '#' && url.slice(0, 2) !== '${') {
            url = 'http://' + url;
        }
        return url;
    },
    /**
     * Abstract method: return true if the URL should be stripped of its domain.
     *
     * @abstract
     * @private
     * @returns {boolean}
     */
    _doStripDomain: function () {},
    /**
     * Get the link's data (url, content and styles).
     *
     * @private
     * @returns {Object} {content: String, url: String, classes: String, isNewWindow: Boolean}
     */
    _getData: function () {
        var $url = this.$('input[name="url"]');
        var url = $url.val();
        var content = this.$('input[name="label"]').val() || url;

        if (!this.isButton && $url.prop('required') && (!url || !$url[0].checkValidity())) {
            return null;
        }

        const type = this._getLinkType();
        const customTextColor = this._getLinkCustomTextColor();
        const customFill = this._getLinkCustomFill();
        const customBorder = this._getLinkCustomBorder();
        const customBorderWidth = this._getLinkCustomBorderWidth();
        const customBorderStyle = this._getLinkCustomBorderStyle();
        const customClasses = this._getLinkCustomClasses();
        const size = this._getLinkSize();
        const shape = this._getLinkShape();
        const shapes = shape ? shape.split(',') : [];
        const style = ['outline', 'fill'].includes(shapes[0]) ? `${shapes[0]}-` : '';
        const shapeClasses = shapes.slice(style ? 1 : 0).join(' ');
        const classes = (this.data.className || '') +
            (type ? (` btn btn-${style}${type}`) : '') +
            (type === 'custom' ? customClasses : '') +
            (type && shapeClasses ? (` ${shapeClasses}`) : '') +
            (type && size ? (' btn-' + size) : '');
        var isNewWindow = this._isNewWindow(url);
        var doStripDomain = this._doStripDomain();
        if (url.indexOf('@') >= 0 && url.indexOf('mailto:') < 0 && !url.match(/^http[s]?/i)) {
            url = ('mailto:' + url);
        } else if (url.indexOf(location.origin) === 0 && doStripDomain) {
            url = url.slice(location.origin.length);
        }
        var allWhitespace = /\s+/gi;
        var allStartAndEndSpace = /^\s+|\s+$/gi;
        return {
            content: content,
            url: this._correctLink(url),
            classes: classes.replace(allWhitespace, ' ').replace(allStartAndEndSpace, ''),
            customTextColor: customTextColor,
            customFill: customFill,
            customBorder: customBorder,
            customBorderWidth: customBorderWidth,
            customBorderStyle: customBorderStyle,
            oldAttributes: this.data.oldAttributes,
            isNewWindow: isNewWindow,
            doStripDomain: doStripDomain,
        };
    },
    /**
     * Return a list of all the descendants of a given element.
     *
     * @private
     * @param {Node} rootNode
     * @returns {Node[]}
     */
    _getDescendants: function (rootNode) {
        const nodes = [];
        for (const node of rootNode.childNodes) {
            nodes.push(node);
            nodes.push(...this._getDescendants(node));
        }
        return nodes;
    },
    /**
     * Abstract method: return a JQuery object containing the UI elements
     * holding the styling options of the link (eg: color, size, shape).
     *
     * @abstract
     * @private
     * @returns {JQuery}
     */
    _getLinkOptions: function () {},
    /**
     * Abstract method: return the shape(s) to apply to the link (eg:
     * "outline", "rounded-circle", "outline,rounded-circle").
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkShape: function () {},
    /**
     * Abstract method: return the size to apply to the link (eg:
     * "sm", "lg").
     *
     * @private
     * @returns {string}
     */
    _getLinkSize: function () {},
    /**
     * Abstract method: return the type to apply to the link (eg:
     * "primary", "secondary").
     *
     * @private
     * @returns {string}
     */
    _getLinkType: function () {},
    /**
     * Returns the custom text color for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomTextColor: function () {},
    /**
     * Returns the custom border color for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomBorder: function () {},
    /**
     * Returns the custom border width for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomBorderWidth: function () {},
    /**
     * Returns the custom border style for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomBorderStyle: function () {},
    /**
     * Returns the custom fill color for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomFill: function () {},
    /**
     * Returns the custom text, fill and border color classes for custom type.
     *
     * @abstract
     * @private
     * @returns {string}
     */
    _getLinkCustomClasses: function () {},
    /**
     * Abstract method: return true if the link should open in a new window.
     *
     * @abstract
     * @private
     * @returns {boolean}
     */
    _isNewWindow: function (url) {},
    /**
     * Abstract method: mark one or several options as active or inactive.
     *
     * @abstract
     * @private
     * @param {JQuery} $option
     * @param {boolean} [active]
     */
    _setSelectOption: function ($option, active) {},
    /**
     * @abstract
     * @private
     */
    _updateOptionsUI: function () {},

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAnyChange: function () {
        this._adaptPreview();
    },
    /**
     * @private
     */
    _onURLInput: function () {
        var $linkUrlInput = this.$('#o_link_dialog_url_input');
        let value = $linkUrlInput.val();
        let isLink = value.indexOf('@') < 0;
        this.$('input[name="is_new_window"]').closest('.form-group').toggleClass('d-none', !isLink);
        this.$('.o_strip_domain').toggleClass('d-none', value.indexOf(window.location.origin) !== 0);
    },
});

return Link;
});
