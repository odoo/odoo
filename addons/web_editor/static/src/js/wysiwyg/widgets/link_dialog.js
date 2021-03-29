odoo.define('wysiwyg.widgets.LinkDialog', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('wysiwyg.widgets.Dialog');
const OdooEditorLib = require('web_editor.odoo-editor');
const wysiwygUtils = require('@web_editor/js/wysiwyg/wysiwyg_utils');

var _t = core._t;

/**
 * Allows to customize link content and style.
 */
var LinkDialog = Dialog.extend({
    template: 'wysiwyg.widgets.link',
    xmlDependencies: (Dialog.prototype.xmlDependencies || []).concat([
        '/web_editor/static/src/xml/wysiwyg.xml'
    ]),
    events: _.extend({}, Dialog.prototype.events || {}, {
        'input': '_onAnyChange',
        'change [name="link_style_color"]': '_onTypeChange',
        'change': '_onAnyChange',
        'input input[name="url"]': '_onURLInput',
    }),

    /**
     * @constructor
     * @param {Boolean} linkInfo.isButton - whether if the target is a button element.
     */
    init: function (parent, options, editable, data, link) {
        this.options = options || {};
        this._super(parent, _.extend({
            title: _t("Link to"),
        }, this.options));

        this.data = data || {};
        this.isButton = this.data.isButton;
        // Using explicit type 'link' to preserve style when the target is <button class="...btn-link"/>.
        this.colorsData = [
            {type: this.isButton ? 'link' : '', label: _t("Link"), btnPreview: 'link'},
            {type: 'primary', label: _t("Primary"), btnPreview: 'primary'},
            {type: 'secondary', label: _t("Secondary"), btnPreview: 'secondary'},
            // Note: by compatibility the dialog should be able to remove old
            // colors that were suggested like the BS status colors or the
            // alpha -> epsilon classes. This is currently done by removing
            // all btn-* classes anyway.
        ];

        this.editable = editable;
        this.$editable = $(editable);
        this.data = data || {};

        this.data.className = this.data.className || "";
        this.data.iniClassName = this.data.iniClassName || "";

        if (link) {
            const range = document.createRange();
            range.selectNodeContents(link);
            this.data.range = range;
        } else {
            const selection = editable && editable.ownerDocument.getSelection();
            this.data.range = selection && selection.rangeCount && selection.getRangeAt(0);
        }

        if (this.data.range) {
            this.needLabel = this.data.range.collapsed;
            let $link;
            if (link) {
                $link = $(link);
            } else {
                const firstLinkInSelection = OdooEditorLib.getInSelection(this.editable.ownerDocument, 'a');
                $link = $(firstLinkInSelection);
            }
            this.data.iniClassName = $link.attr("class") || "";
            this.colorCombinationClass = false;
            let $node = $link;
            while ($node.length && !$node.is('body')) {
                const className = $node.attr('class') || '';
                const m = className.match(/\b(o_cc\d+)\b/g);
                if (m) {
                    this.colorCombinationClass = m[0];
                    break;
                }
                $node = $node.parent();
            }
            this.data.className = this.data.iniClassName.replace(/(^|\s+)btn(-[a-z0-9_-]*)?/gi, ' ');

            let textLink = link;
            if (!textLink) {
                const startLink = $(this.data.range.startContainer).closest('a')[0];
                const endLink = $(this.data.range.endContainer).closest('a')[0];
                const isLink = startLink && (startLink === endLink);
                textLink = isLink ? startLink : this.data.range.cloneContents();
            }
            const [encodedText, images] = wysiwygUtils.encodeNodeToText(textLink);
            this.data.originalText = wysiwygUtils.decodeText(encodedText, images);
            this.data.content = encodedText;
            this.data.images = images;
            this.data.url = $link.attr('href') || '';
        } else {
            this.data.content = this.data.content ? this.data.content.replace(/[ \t\r\n]+/g, ' ') : '';
            this.needLabel = true;
        }

        var allBtnClassSuffixes = /(^|\s+)btn(-[a-z0-9_-]*)?/gi;
        var allBtnShapes = /\s*(rounded-circle|flat)\s*/gi;
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
        this.buttonOptsCollapseEl = this.el.querySelector('#o_link_dialog_button_opts_collapse');

        this.$styleInputs = this.$('input.link-style');
        this.$styleInputs.prop('checked', false).filter('[value=""]').prop('checked', true);
        if (this.data.iniClassName) {
            _.each(this.$('input[name="link_style_color"], select[name="link_style_size"] > option, select[name="link_style_shape"] > option'), el => {
                var $option = $(el);
                if ($option.val() && this.data.iniClassName.match(new RegExp('(^|btn-| |btn-outline-)' + $option.val()))) {
                    if ($option.is("input")) {
                        $option.prop("checked", true);
                    } else {
                        $option.parent().find('option').removeAttr('selected').removeProp('selected');
                        $option.parent().val($option.val());
                        $option.attr('selected', 'selected').prop('selected', 'selected');
                    }
                }
            });
        }
        if (this.data.url) {
            var match = /mailto:(.+)/.exec(this.data.url);
            this.$('input[name="url"]').val(match ? match[1] : this.data.url);
            this._onURLInput();
        }

        this._updateOptionsUI();
        this._adaptPreview();

        this.$('input:visible:first').focus();

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        var data = this._getData();
        if (data === null) {
            var $url = this.$('input[name="url"]');
            $url.closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            $url.focus();
            return Promise.reject();
        }
        this.data.content = data.content;
        this.data.url = data.url;
        var allWhitespace = /\s+/gi;
        var allStartAndEndSpace = /^\s+|\s+$/gi;
        var allBtnTypes = /(^|[ ])(btn-secondary|btn-success|btn-primary|btn-info|btn-warning|btn-danger)([ ]|$)/gi;
        this.data.className = data.classes.replace(allWhitespace, ' ').replace(allStartAndEndSpace, '');
        if (data.classes.replace(allBtnTypes, ' ')) {
            this.data.style = {
                'background-color': '',
                'color': '',
            };
        }
        this.data.isNewWindow = data.isNewWindow;
        this.final_data = this.data;
        const returnValue = this._super.apply(this, arguments);
        if (this.insertedAnchors && this.insertedAnchors.length) {
            $(this.insertedAnchors[this.insertedAnchors.length - 1]).focus();
        }
        return returnValue;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adapt the link preview to changes.
     *
     * @private
     */
    _adaptPreview: function () {
        var data = this._getData();
        if (data === null) {
            return;
        }
        const attrs = {
            target: '_blank',
            href: data.url && data.url.length ? data.url : '#',
            class: `${data.classes.replace(/float-\w+/, '')} o_btn_preview`,
        };
        this.$("#link-preview").attr(attrs).html((data.content && data.content.length) ? data.content : data.url);
    },

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
        content = wysiwygUtils.decodeText(content, this.data.images);

        if (!this.isButton && $url.prop('required') && (!url || !$url[0].checkValidity())) {
            return null;
        }

        const type = this.$('input[name="link_style_color"]:checked').val() || '';
        const size = this.$('select[name="link_style_size"]').val() || '';
        const shape = this.$('select[name="link_style_shape"]').val() || '';
        const shapes = shape ? shape.split(',') : [];
        const style = ['outline', 'fill'].includes(shapes[0]) ? `${shapes[0]}-` : '';
        const shapeClasses = shapes.slice(style ? 1 : 0).join(' ');
        const classes = (this.data.className || '') +
            (type ? (` btn btn-${style}${type}`) : '') +
            (shapeClasses ? (` ${shapeClasses}`) : '') +
            (size ? (' btn-' + size) : '');
        var isNewWindow = this.options.forceNewWindow ?
            this._isFromAnotherHostName(url) : this.$('input[name="is_new_window"]').prop('checked');
        if (url.indexOf('@') >= 0 && url.indexOf('mailto:') < 0 && !url.match(/^http[s]?/i)) {
            url = ('mailto:' + url);
        } else if (url.indexOf(location.origin) === 0 && this.$('#o_link_dialog_url_strip_domain').prop("checked")) {
            url = url.slice(location.origin.length);
        }
        var allWhitespace = /\s+/gi;
        var allStartAndEndSpace = /^\s+|\s+$/gi;
        return {
            content: content,
            url: this._correctLink(url),
            classes: classes.replace(allWhitespace, ' ').replace(allStartAndEndSpace, ''),
            isNewWindow: isNewWindow,
        };
    },
    /**
     * @private
     */
    _updateOptionsUI: function () {
        const el = this.el.querySelector('[name="link_style_color"]:checked');
        $(this.buttonOptsCollapseEl).collapse(el && el.value ? 'show' : 'hide');
    },
    /**
     * @private
     */
    _isFromAnotherHostName: function (url) {
        if (url.includes(window.location.hostname)) {
            return false;
        }
        try {
            const Url = URL || window.URL || window.webkitURL;
            const urlObj = url.startsWith('/') ? new Url(url, window.location.origin) : new Url(url);
            return (urlObj.origin !== window.location.origin);
        } catch (ignored) {
            return true;
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
        this._adaptPreview();
    },
    /**
     * @private
     */
    _onTypeChange() {
        this._updateOptionsUI();
    },
    /**
     * @private
     */
    _onURLInput: function () {
        var $linkUrlInput = this.$('#o_link_dialog_url_input');
        $linkUrlInput.closest('.form-group').removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
        let value = $linkUrlInput.val();
        let isLink = value.indexOf('@') < 0;
        this.$('input[name="is_new_window"]').closest('.form-group').toggleClass('d-none', !isLink);
        this.$('.o_strip_domain').toggleClass('d-none', value.indexOf(window.location.origin) !== 0);
    },
});

return LinkDialog;
});
