odoo.define('wysiwyg.widgets.LinkTools', function (require) {
'use strict';

const core = require('web.core');
const OdooEditorLib = require('web_editor.odoo-editor');
const Widget = require('web.Widget');
const wysiwygUtils = require('@web_editor/js/wysiwyg/wysiwyg_utils');

const getInSelection = OdooEditorLib.getInSelection;
const getDeepRange = OdooEditorLib.getDeepRange;
const setCursor = OdooEditorLib.setCursor;
const nodeSize = OdooEditorLib.nodeSize;

const _t = core._t;

/**
 * Allows to customize link content and style.
 */
const LinkTools = Widget.extend({
    template: 'wysiwyg.widgets.linkTools',
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
    events: {
        'input': '_onAnyChange',
        'change': '_onAnyChange',
        'input input[name="url"]': '_onURLInput',
        'click we-select we-button': '_onPickSelectOption',
        'click we-checkbox': '_onClickCheckbox',
    },

    /**
     * @constructor
     */
    init: function (parent, options, editable, $button, link) {
        this.options = options || {};
        this._super(parent, _.extend({
            title: _t("Link to"),
        }, this.options));

        this.$button = $button;
        this.colorsData = [
            {type: '', label: _t("Link"), btnPreview: 'link'},
            {type: 'primary', label: _t("Primary"), btnPreview: 'primary'},
            {type: 'secondary', label: _t("Secondary"), btnPreview: 'secondary'},
            // Note: by compatibility the dialog should be able to remove old
            // colors that were suggested like the BS status colors or the
            // alpha -> epsilon classes. This is currently done by removing
            // all btn-* classes anyway.
        ];

        this.editable = editable;
        this.$editable = $(editable);
        this.data = {};

        this.data.className = "";
        this.data.iniClassName = "";

        this.data.range = editable.ownerDocument.getSelection().getRangeAt(0);

        this.$link = this._getOrCreateLink(link);
        this.data.iniClassName = this.$link.attr("class") || "";
        this.colorCombinationClass = '';

        const allBtnClassSuffixes = /(^|\s+)btn(-[a-z0-9_-]*)?/gi;
        this.data.className = this.data.iniClassName.replace(allBtnClassSuffixes, ' ');
        const [encodedText, images] = wysiwygUtils.encodeNodeToText(this.$link[0]);
        this.data.text = encodedText;
        this.data.originalText = wysiwygUtils.decodeText(encodedText, images);
        this.data.images = images;
        this.data.oldAttributes = this.$link.getAttributes();
        this.data.url = this.$link.attr('href');
        this.data.isNewWindow = this.$link.attr('target') === '_blank';

        const allBtnShapes = /\s*(rounded-circle|flat)\s*/gi;
        this.data.className = this.data.iniClassName
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
        this.$button.addClass('active');

        if (this.data.iniClassName) {
            const options = [
                'we-selection-items[name="link_style_color"] > we-button',
                'we-selection-items[name="link_style_size"] > we-button',
                'we-selection-items[name="link_style_shape"] > we-button',
            ];
            for (const option of this.$(options.join(','))) {
                const $option = $(option);
                const value = $option.data('value');
                let active = false;
                if (value) {
                    const subValues = value.split(',');
                    let subActive = true;
                    for (let subValue of subValues) {
                        const classPrefix = new RegExp('(^|btn-| |btn-outline-)' + subValue);
                        subActive = subActive && classPrefix.test(this.data.iniClassName);
                    }
                    active = subActive;
                } else {
                    active = !this.data.iniClassName.includes('btn-');
                }
                this._setSelectOption($option, active);
            }
        }
        if (this.data.url) {
            var match = /mailto:(.+)/.exec(this.data.url);
            this.$('input[name="url"]').val(match ? match[1] : this.data.url);
            this._onURLInput();
        }
        if (this.data.isNewWindow) {
            this.$('we-button.o_we_checkbox_wrapper').toggleClass('active', true);
        }

        this._updateOptionsUI();
        this._adaptLink(false);

        this.$('input:visible:first').focus();

        return this._super.apply(this, arguments);
    },
    destroy: function () {
        this.options.wysiwyg.odooEditor.automaticStepSkipStack();
        $('.oe_edited_link').removeClass('oe_edited_link');
        const $contents = this.$link.contents();
        if (!this.$link.attr('href') && !this.colorCombinationClass) {
            $contents.unwrap();
        }
        this.$button.removeClass('active');
        const start = $contents[0] || this.$link[0];
        const end = $contents[$contents.length - 1] || this.$link[0];
        setCursor(start, 0, end, nodeSize(end));
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adapt the link to changes.
     *
     * @private
     */
    _adaptLink: function (createStep = true) {
        var data = this._getData();
        if (data === null) {
            return;
        }
        const attrs = Object.assign({}, this.data.oldAttributes, {
            target: data.isNewWindow ? '_blank' : '',
            href: data.url,
            class: `${data.classes}`,
        });
        const $links = $('.oe_edited_link');
        $links.removeClass('oe_edited_link');
        this.$link.attr(attrs);
        if (data.label !== this.data.originalText || data.url !== this.data.url) {
            const label = (data.label && data.label.length) ? data.label : data.url;
            this.$link.html(label);
        }
        if (createStep) {
            this.options.wysiwyg.odooEditor.historyStep();
        }
        this.options.wysiwyg.odooEditor.automaticStepSkipStack();
        $links.addClass('oe_edited_link');
    },
    /**
     * Get the link's data (url, label and styles).
     *
     * @private
     * @returns {Object} {label: String, url: String, classes: String, isNewWindow: Boolean}
     */
    _getData: function () {
        var $url = this.$('input[name="url"]');
        var url = $url.val();
        var label = this.$('input[name="label"]').val() || url;

        if (label && this.data.images) {
            label = wysiwygUtils.decodeText(label, this.data.images);
        }

        if (!this.isButton && $url.prop('required') && (!url || !$url[0].checkValidity())) {
            return null;
        }

        const type = this.$('we-selection-items[name="link_style_color"] we-button.active').data('value') || '';
        const size = this.$('we-selection-items[name="link_style_size"] we-button.active').data('value') || '';
        const shape = this.$('we-selection-items[name="link_style_shape"] we-button.active').data('value') || '';
        const shapes = shape ? shape.split(',') : [];
        const style = ['outline', 'fill'].includes(shapes[0]) ? `${shapes[0]}-` : '';
        const shapeClasses = shapes.slice(style ? 1 : 0).join(' ');
        const classes = (this.data.className || '') +
            (type ? (` btn btn-${style}${type}`) : '') +
            (type && shapeClasses ? (` ${shapeClasses}`) : '') +
            (type && size ? (' btn-' + size) : '');
        var isNewWindow = this.$('we-checkbox[name="is_new_window"]').closest('we-button.o_we_checkbox_wrapper').hasClass('active');
        var doStripDomain = this.$('we-checkbox[name="do_strip_domain"]').closest('we-button.o_we_checkbox_wrapper').hasClass('active');
        if (url.indexOf('@') >= 0 && url.indexOf('mailto:') < 0 && !url.match(/^http[s]?/i)) {
            url = ('mailto:' + url);
        } else if (url.indexOf(location.origin) === 0 && doStripDomain) {
            url = url.slice(location.origin.length);
        }
        var allWhitespace = /\s+/gi;
        var allStartAndEndSpace = /^\s+|\s+$/gi;
        return {
            label: label,
            url: this._correctLink(url),
            classes: classes.replace(allWhitespace, ' ').replace(allStartAndEndSpace, '').replace(/oe_edited_link/, ''),
            oldAttributes: this.data.oldAttributes,
            isNewWindow: isNewWindow,
            doStripDomain: doStripDomain,
        };
    },
    _getOrCreateLink: function (linkToEdit) {
        this.options.wysiwyg.odooEditor.automaticStepSkipStack();
        const doc = this.editable.ownerDocument;
        const range = getDeepRange(this.editable, {splitText: true, select: true, correctTripleClick: true});
        this.needLabel = false;
        let link = linkToEdit || getInSelection(doc, 'a');
        const $link = $(link);
        if (link && !linkToEdit && (!$link.has(range.startContainer).length || !$link.has(range.endContainer).length)) {
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
        link.classList.add('oe_edited_link');
        return $(link);
    },
    _setSelectOption: function ($option, active) {
        $option.toggleClass('active', active);
        if (active) {
            $option.closest('we-select').find('we-toggler').text($option.text());
            // ensure only one option is active in the dropdown
            $option.siblings('we-button').removeClass("active");
        }
    },
    /**
     * @private
     */
    _updateOptionsUI: function () {
        const el = this.el.querySelector('[name="link_style_color"] we-button.active');
        if (el) {
            this.colorCombinationClass = el.dataset.value;
            // Hide the size and shape options if the link is an unstyled anchor.
            this.$('.link-size-row, .link-shape-row').toggleClass('d-none', !this.colorCombinationClass);
        }
    },
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

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAnyChange: function () {
        this._adaptLink();
    },
    _onClickCheckbox: function (ev) {
        const $target = $(ev.target);
        $target.closest('we-button.o_we_checkbox_wrapper').toggleClass('active');
        this._adaptLink();
    },
    _onPickSelectOption: function (ev) {
        const $target = $(ev.target);
        const $select = $target.closest('we-select');
        $select.find('we-selection-items we-button').toggleClass('active', false);
        this._setSelectOption($target, true);
        this._updateOptionsUI();
        this._adaptLink();
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

return LinkTools;
});
