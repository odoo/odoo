odoo.define('wysiwyg.widgets.LinkDialog', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('wysiwyg.widgets.Dialog');

var dom = $.summernote.core.dom;
var range = $.summernote.core.range;

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
        'change': '_onAnyChange',
        'input input[name="url"]': '_onURLInput',
    }),

    /**
     * @constructor
     */
    init: function (parent, options, editable, linkInfo) {
        var self = this;
        this.options = options || {};

        this._super(parent, _.extend({
            title: _t("Link to"),
        }, this.options));

        this.trigger_up('getRecordInfo', {
            recordInfo: this.options,
            callback: function (recordInfo) {
                _.defaults(self.options, recordInfo);
            },
        });

        this.editable = editable;
        this.data = linkInfo || {};

        this.data.className = "";
        this.data.iniClassName = "";

        var r = this.data.range;
        this.needLabel = !r || (r.sc === r.ec && r.so === r.eo);

        if (this.data.range) {
            this.data.iniClassName = $(this.data.range.sc).filter("a").attr("class") || "";
            this.data.className = this.data.iniClassName.replace(/(^|\s+)btn(-[a-z0-9_-]*)?/gi, ' ');

            var is_link = this.data.range.isOnAnchor();

            var sc = r.sc;
            var so = r.so;
            var ec = r.ec;
            var eo = r.eo;

            var nodes;
            if (!is_link) {
                if (sc.tagName) {
                    sc = dom.firstChild(so ? sc.childNodes[so] : sc);
                    so = 0;
                } else if (so !== sc.textContent.length) {
                    if (sc === ec) {
                        ec = sc = sc.splitText(so);
                        eo -= so;
                    } else {
                        sc = sc.splitText(so);
                    }
                    so = 0;
                }
                if (ec.tagName) {
                    ec = dom.lastChild(eo ? ec.childNodes[eo-1] : ec);
                    eo = ec.textContent.length;
                } else if (eo !== ec.textContent.length) {
                    ec.splitText(eo);
                }

                nodes = dom.listBetween(sc, ec);

                // browsers can't target a picture or void node
                if (dom.isVoid(sc) || dom.isImg(sc)) {
                    so = dom.listPrev(sc).length-1;
                    sc = sc.parentNode;
                }
                if (dom.isBR(ec)) {
                    eo = dom.listPrev(ec).length-1;
                    ec = ec.parentNode;
                } else if (dom.isVoid(ec) || dom.isImg(sc)) {
                    eo = dom.listPrev(ec).length;
                    ec = ec.parentNode;
                }

                this.data.range = range.create(sc, so, ec, eo);
                $(editable).data("range", this.data.range);
                this.data.range.select();
            } else {
                nodes = dom.ancestor(sc, dom.isAnchor).childNodes;
            }

            if (dom.isImg(sc) && nodes.indexOf(sc) === -1) {
                nodes.push(sc);
            }
            if (nodes.length > 1 || dom.ancestor(nodes[0], dom.isImg)) {
                var text = "";
                this.data.images = [];
                for (var i=0; i<nodes.length; i++) {
                    if (dom.ancestor(nodes[i], dom.isImg)) {
                        this.data.images.push(dom.ancestor(nodes[i], dom.isImg));
                        text += '[IMG]';
                    } else if (!is_link && nodes[i].nodeType === 1) {
                        // just use text nodes from listBetween
                    } else if (!is_link && i===0) {
                        text += nodes[i].textContent.slice(so, Infinity);
                    } else if (!is_link && i===nodes.length-1) {
                        text += nodes[i].textContent.slice(0, eo);
                    } else {
                        text += nodes[i].textContent;
                    }
                }
                this.data.text = text;
            }
        }

        this.data.text = this.data.text.replace(/[ \t\r\n]+/g, ' ');

        var allBtnClassSuffixes = /(^|\s+)btn(-[a-z0-9_-]*)?/gi;
        var allBtnShapes = /\s*(rounded-circle|flat)\s*/gi;
        this.data.className = this.data.iniClassName
            .replace(allBtnClassSuffixes, ' ')
            .replace(allBtnShapes, ' ');
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.$('input.link-style').prop('checked', false).first().prop('checked', true);
        if (this.data.iniClassName) {
            this.$('input[name="link_style_color"], select[name="link_style_size"] > option, select[name="link_style_shape"] > option').each(function () {
                var $option = $(this);
                if ($option.val() && self.data.iniClassName.match(new RegExp('(^|btn-| |btn-outline-)' + $option.val()))) {
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

        // Hide the duplicate color buttons (most of the times, primary = alpha
        // and secondary = beta for example but this may depend on the theme)
        this.opened().then(function () {
            var colors = [];
            _.each(self.$('.o_link_dialog_color .o_btn_preview'), function (btn) {
                var $btn = $(btn);
                var color = $btn.css('background-color');
                if (_.contains(colors, color)) {
                    $btn.hide(); // Not remove to be able to edit buttons with those styles
                } else {
                    colors.push(color);
                }
            });
        });

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
        this.data.text = data.label;
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
        return this._super.apply(this, arguments);
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
        var $preview = this.$("#link-preview");
        var data = this._getData();
        if (data === null) {
            return;
        }
        var floatClass = /float-\w+/;
        $preview.attr({
            target: data.isNewWindow ? '_blank' : '',
            href: data.url && data.url.length ? data.url : '#',
            class: data.classes.replace(floatClass, '') + ' o_btn_preview',
        }).html((data.label && data.label.length) ? data.label : data.url);
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
            for (var i = 0; i < this.data.images.length; i++) {
                label = label.replace('<', "&lt;").replace('>', "&gt;").replace(/\[IMG\]/, this.data.images[i].outerHTML);
            }
        }

        if ($url.prop('required') && (!url || !$url[0].checkValidity())) {
            return null;
        }

        var style = this.$('input[name="link_style_color"]:checked').val() || '';
        var shape = this.$('select[name="link_style_shape"] option:selected').val() || '';
        var size = this.$('select[name="link_style_size"] option:selected').val() || '';
        var shapes = shape.split(',');
        var outline = shapes[0] === 'outline';
        shape = shapes.slice(outline ? 1 : 0).join(' ');
        var classes = (this.data.className || '') +
            (style ? (' btn btn-' + (outline ? 'outline-' : '') + style) : '') +
            (shape ? (' ' + shape) : '') +
            (size ? (' btn-' + size) : '');
        var isNewWindow = this.$('input[name="is_new_window"]').prop('checked');

        if (url.indexOf('@') >= 0 && url.indexOf('mailto:') < 0 && !url.match(/^http[s]?/i)) {
            url = ('mailto:' + url);
        } else if (url.indexOf(location.origin) === 0 && this.$('#o_link_dialog_url_strip_domain').prop("checked")) {
            url = url.slice(location.origin.length);
        }
        var allWhitespace = /\s+/gi;
        var allStartAndEndSpace = /^\s+|\s+$/gi;
        return {
            label: label,
            url: url,
            classes: classes.replace(allWhitespace, ' ').replace(allStartAndEndSpace, ''),
            isNewWindow: isNewWindow,
        };
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
