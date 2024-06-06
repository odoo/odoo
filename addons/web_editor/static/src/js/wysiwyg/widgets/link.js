odoo.define('wysiwyg.widgets.Link', function (require) {
'use strict';

const core = require('web.core');
const OdooEditorLib = require('@web_editor/js/editor/odoo-editor/src/OdooEditor');
const Widget = require('web.Widget');
const {isColorGradient} = require('web_editor.utils');

const getDeepRange = OdooEditorLib.getDeepRange;
const getInSelection = OdooEditorLib.getInSelection;
const EMAIL_REGEX = OdooEditorLib.EMAIL_REGEX;
const _t = core._t;

/**
 * Allows to customize link content and style.
 */
const Link = Widget.extend({
    events: {
        'input': '_onAnyChange',
        'change': '_onAnyChange',
        'input input[name="url"]': '__onURLInput',
        'change input[name="url"]': '_onURLInputChange',
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

        // The classes in the following array should not be in editable areas
        // but as there are still some (e.g. in the "newsletter block" snippet)
        // we make sure the options system works with them.
        this.toleratedClasses = ['btn-link', 'btn-success'];

        this.editable = editable;
        this.$editable = $(editable);

        if (link) {
            const range = document.createRange();
            range.selectNodeContents(link);
            this.data.range = range;
            this.$link = $(link);
            this.linkEl = link;
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
            const linkNode = this.linkEl || this.data.range.cloneContents();
            const linkText = linkNode.innerText.replaceAll("\u200B", "");
            this.data.content = linkText.replace(/[ \t\r\n]+/g, ' ');
            this.data.originalText = this.data.content;
            if (linkNode instanceof DocumentFragment) {
                this.data.originalHTML = $('<fakeEl>').append(linkNode).html();
            } else {
                this.data.originalHTML = linkNode.innerHTML;
            }
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

        const classesToKeep = [
            'text-wrap', 'text-nowrap', 'text-start', 'text-center', 'text-end',
            'text-truncate',
        ];
        const keptClasses = this.data.iniClassName.split(' ').filter(className => classesToKeep.includes(className));
        const allBtnColorPrefixes = /(^|\s+)(bg|text|border)((-[a-z0-9_-]*)|\b)/gi;
        const allBtnClassSuffixes = /(^|\s+)btn((-[a-z0-9_-]*)|\b)/gi;
        const allBtnShapes = /\s*(rounded-circle|flat)\s*/gi;
        this.data.className = this.data.iniClassName
            .replace(allBtnColorPrefixes, ' ')
            .replace(allBtnClassSuffixes, ' ')
            .replace(allBtnShapes, ' ');
        this.data.className += ' ' + keptClasses.join(' ');
        // 'o_submit' class will force anchor to be handled as a button in linkdialog.
        if (/(?:s_website_form_send|o_submit)/.test(this.data.className)) {
            this.isButton = true;
        }

        this.renderingPromise = new Promise(resolve => this._renderingResolver = resolve);
    },
    /**
     * @override
     */
    start: async function () {
        for (const option of this._getLinkOptions()) {
            const $option = $(option);
            const value = $option.is('input') ? $option.val() : $option.data('value') || option.getAttribute('value');
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
                active = !this.data.iniClassName
                         || this.toleratedClasses.some(val => this.data.iniClassName.split(' ').includes(val))
                         || !this.data.iniClassName.includes('btn-');
            }
            this._setSelectOption($option, active);
        }

        const _super = this._super.bind(this);

        this._updateOptionsUI();

        if (this.data.url) {
            this._updateUrlInput(this.data.url);
        }

        if (!this.noFocusUrl) {
            this.focusUrl();
        }

        return _super(...arguments);
    },
    /**
     * @private
     */
    async _widgetRenderAndInsert() {
        const res = await this._super(...arguments);

        // TODO find a better solution than this during the upcoming refactoring
        // of the link tools / link dialog.
        if (this._renderingResolver) {
            this._renderingResolver();
        }

        return res;
    },
    /**
     * @override
     */
    destroy () {
        if (this._savedURLInputOnDestroy) {
            this._adaptPreview();
        }
        this._super(...arguments);
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
        // Same thing for the "btn-success" class, this class cannot be added
        // by the options but we still have to ensure that it is not removed if
        // it exists in a template (e.g. "Newsletter Block" snippet).
        if (!data.classes.split(' ').includes('btn')) {
            for (const linkClass of this.toleratedClasses) {
                if (this.data.iniClassName && this.data.iniClassName.split(' ').includes(linkClass)) {
                    data.classes += " btn " + linkClass;
                }
            }
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
        if (typeof data.classes === "string") {
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
        this._updateLinkContent(this.$link, data);
    },
    /**
     * Focuses the url input.
     */
    focusUrl() {
        const urlInput = this.el.querySelector('input[name="url"]');
        urlInput.focus();
        urlInput.select();
    },

    /**
     * Return the link element to edit. Create one from selection if none was
     * present in selection.
     *
     * @param {Node} [options.containerNode]
     * @param {Node} [options.startNode]
     * @returns {Object}
     */
    getOrCreateLink (options) {
        Link.getOrCreateLink(options);
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
        if (url.indexOf('tel:') === 0) {
            url = url.replace(/^tel:([0-9]+)$/, 'tel://$1');
        } else if (url && !url.startsWith('mailto:') && url.indexOf('://') === -1
                    && url[0] !== '/' && url[0] !== '#' && url.slice(0, 2) !== '${') {
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
        const emailMatch = url.match(EMAIL_REGEX);
        if (emailMatch) {
            url = emailMatch[1] ? emailMatch[0] : 'mailto:' + emailMatch[0];
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
     * holding the "Open in new window" option's row of the link.
     *
     * @abstract
     * @private
     * @returns {JQuery}
     */
    _getIsNewWindowFormRow() {},
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
     * Update the link content.
     *
     * @private
     * @param {JQuery} $link
     * @param {object} linkInfos
     * @param {boolean} force
     */
    _updateLinkContent($link, linkInfos, { force = false } = {}) {
        if (force || (this._setLinkContent && (linkInfos.content !== this.data.originalText || linkInfos.url !== this.data.url))) {
            if (linkInfos.content === this.data.originalText) {
                $link.html(this.data.originalHTML);
            } else if (linkInfos.content && linkInfos.content.length) {
                $link.text(linkInfos.content);
            } else {
                $link.text(linkInfos.url);
            }
        }
    },
    /**
     * @abstract
     * @private
     */
    _updateOptionsUI: function () {},
    /**
     * @private
     * @param {String} url
     */
    _updateUrlInput: function (url) {
        if (!this.el) {
            return;
        }
        const match = /mailto:(.+)/.exec(url);
        this.el.querySelector('input[name="url"]').value = match ? match[1] : url;
        this._onURLInput();
        this._savedURLInputOnDestroy = false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAnyChange: function (e) {
        if (!e.target.closest('input[type="text"]')) {
            this._adaptPreview();
        }
    },
    /**
     * @todo Adapt in master: in stable _onURLInput was both used as an event
     * handler responding to url input events + a private method called at the
     * widget lifecycle start. Originally both points were to update the link
     * tools/dialog UI. It was later wanted to actually update the DOM... but
     * should only be done in event handler part.
     *
     * This allows to differentiate the event handler part. In master, we should
     * take the opportunity to also update the `_updatePreview` concept which
     * updates the "preview" of the original link dialog but actually updates
     * the real DOM for the "new" link tools.
     *
     * @private
     */
    __onURLInput: function () {
        this._onURLInput(...arguments);
    },
    /**
     * @private
     */
    _onURLInput: function () {
        this._savedURLInputOnDestroy = true;
        var $linkUrlInput = this.$('#o_link_dialog_url_input');
        let value = $linkUrlInput.val();
        let isLink = !EMAIL_REGEX.test(value);
        this._getIsNewWindowFormRow().toggleClass('d-none', !isLink);
        this.$('.o_strip_domain').toggleClass('d-none', value.indexOf(window.location.origin) !== 0);
    },
    /**
     * @private
     */
    _onURLInputChange: function () {
        this._adaptPreview();
        this._savedURLInputOnDestroy = false;
    },
});

/**
 * Return the link element to edit. Create one from selection if none was
 * present in selection.
 *
 * @param {Node} [options.containerNode]
 * @param {Node} [options.startNode]
 * @returns {Object}
 */
Link.getOrCreateLink = ({ containerNode, startNode } = {})  => {

    if (startNode) {
        if ($(startNode).is('a')) {
            return { link: startNode, needLabel: false };
        } else {
            $(startNode).wrap('<a href="#"/>');
            return { link: startNode.parentElement, needLabel: false };
        }
    }

    const doc = containerNode && containerNode.ownerDocument || document;
    let needLabel = false;
    let link = getInSelection(doc, 'a');
    const $link = $(link);
    const range = getDeepRange(containerNode, {splitText: true, select: true, correctTripleClick: true});
    if (!range) {
        return {};
    }
    const isContained = containerNode.contains(range.startContainer) && containerNode.contains(range.endContainer);
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
    } else if (!link && isContained) {
        link = document.createElement('a');
        if (range.collapsed) {
            range.insertNode(link);
            needLabel = true;
        } else {
            link.appendChild(range.extractContents());
            range.insertNode(link);
        }
    }
    return { link, needLabel };
};

return Link;
});
