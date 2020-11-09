odoo.define('wysiwyg.widgets.LinkDialog', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('wysiwyg.widgets.Dialog');


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
     * @param {} [options.props.text]
     * @param {} [options.props.className]
     */
    init: function (parent, options) {
        const self = this;
        this._super(parent, _.extend({
            title: _t("Link to"),
        }, this.options));

        this.colorsData = [
            {type: '', label: _t("Link"), btnPreview: 'link'},
            {type: 'primary', label: _t("Primary"), btnPreview: 'primary'},
            {type: 'secondary', label: _t("Secondary"), btnPreview: 'secondary'},
            // Note: by compatibility the dialog should be able to remove old
            // colors that were suggested like the BS status colors or the
            // alpha -> epsilon classes. This is currently done by removing
            // all btn-* classes anyway.
        ];

        this.trigger_up('getRecordInfo', {
            recordInfo: this.options,
            callback: function (recordInfo) {
                _.defaults(self.options, recordInfo);
            },
        });

        // data is used in the dialog template.
        this.props = options.props || {};

        this.__editorEditable = this.props.__editorEditable;
        this.colorCombinationClass = this.props.colorCombinationClass;

        var allBtnClassSuffixes = /(^|\s+)btn(-[a-z0-9_-]*)?/gi;
        var allBtnShapes = /\s*(rounded-circle|flat)\s*/gi;
        const cleanClassNames = !this.props.initialClassNames ? '' :
            this.props.initialClassNames
                .replace(allBtnClassSuffixes, ' ')
                .replace(allBtnShapes, ' ');

        this.state = {
            needLabel: !this.props.text || !this.props.text.length || this.props.needLabel,
            text: this.props.text,
            images: this.props.images,
            className: cleanClassNames,
            url: this.props.url,
            isNewWindow: this.props.isNewWindow,
        };
    },
    /**
     * @override
     */
    start: function () {
        const self = this;
        this.buttonOptsCollapseEl = this.el.querySelector('#o_link_dialog_button_opts_collapse');

        this.$('input.link-style').prop('checked', false).first().prop('checked', true);
        if (this.props.initialClassNames) {
            this.$('input[name="link_style_color"], select[name="link_style_size"] > option, select[name="link_style_shape"] > option').each(function () {
                var $option = $(this);
                if ($option.val() && self.props.initialClassNames.match(new RegExp('(^|btn-| |btn-outline-)' + $option.val()))) {
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
        if (this.state.url) {
            var match = /mailto:(.+)/.exec(this.state.url);
            this.$('input[name="url"]').val(match ? match[1] : this.state.url);
            this._onURLInput();
        }

        this._updateOptionsUI();
        this._adaptPreview();

        this.opened(() => {
            // We need to wait to be sure to trigger focus() the tick after the Event normaliser mess with events
           setTimeout(() => self.$('input:visible:first').focus(), 0);
        });

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        const data = this._getData();
        if (data === null) {
            var $url = this.$('input[name="url"]');
            $url.closest('.form-group').addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            $url.focus();
            return Promise.reject();
        }

        this.final_data = {
            needLabel: this.state.needLabel,
            text: data.label,
            url: data.url,
            isNewWindow: data.isNewWindow,
            classes: data.classes,
        };
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
        var data = this._getData();
        if (data === null) {
            return;
        }
        const attrs = {
            target: data.isNewWindow ? '_blank' : '',
            href: data.url && data.url.length ? data.url : '#',
            class: `${data.classes.replace(/float-\w+/, '')} o_btn_preview`,
        };
        const $preview = this.$("#link-preview");
        const $a = $preview.find('a:first');
        $a.siblings().remove();

        const labels = (data.label && data.label.length) ? data.label.split('\n') : [data.url];

        for (const label of labels) {
            $preview.append($a.clone().attr(attrs).html(label));
        }
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
        var label = this.state.text;
        if (this.state.needLabel) {
            label = this.$('input[name="label"]').val() || url || '';
            label = label.replace('<', "&lt;").replace('>', "&gt;");
        }
        if (this.state.images) {
            for (var i = 0; i < this.state.images.length; i++) {
                label = label.replace(/\[IMG\]/, this.state.images[i]);
            }
        }

        if ($url.prop('required') && (!url || !$url[0].checkValidity())) {
            return null;
        }

        const type = this.$('input[name="link_style_color"]:checked').val() || '';
        const size = this.$('select[name="link_style_size"]').val() || '';
        const shape = this.$('select[name="link_style_shape"]').val() || '';
        const shapes = shape ? shape.split(',') : [];
        const style = ['outline', 'fill'].includes(shapes[0]) ? `${shapes[0]}-` : '';
        const shapeClasses = shapes.slice(style ? 1 : 0).join(' ');
        const classes = (this.state.className || '') +
            (type ? (` btn btn-${style}${type}`) : '') +
            (shapeClasses ? (` ${shapeClasses}`) : '') +
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
    /**
     * @private
     */
    _updateOptionsUI: function () {
        const el = this.el.querySelector('[name="link_style_color"]:checked');
        $(this.buttonOptsCollapseEl).collapse(el && el.value ? 'show' : 'hide');
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
