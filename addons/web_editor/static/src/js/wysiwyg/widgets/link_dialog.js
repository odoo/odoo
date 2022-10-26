odoo.define('wysiwyg.widgets.LinkDialog', function (require) {
'use strict';

const Dialog = require('wysiwyg.widgets.Dialog');
const Link = require('wysiwyg.widgets.Link');


// This widget is there only to extend Link and be instantiated by LinkDialog.
const _DialogLinkWidget = Link.extend({
    template: 'wysiwyg.widgets.link',
    events: _.extend({}, Link.prototype.events || {}, {
        'change [name="link_style_color"]': '_onTypeChange',
    }),

    /**
     * @override
     */
    start: function () {
        this.buttonOptsCollapseEl = this.el.querySelector('#o_link_dialog_button_opts_collapse');
        this.$styleInputs = this.$('input.link-style');
        this.$styleInputs.prop('checked', false).filter('[value=""]').prop('checked', true);
        if (this.data.isNewWindow) {
            this.$('we-button.o_we_checkbox_wrapper').toggleClass('active', true);
        }
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
            $url.closest('.o_url_input').addClass('o_has_error').find('.form-control, .form-select').addClass('is-invalid');
            $url.focus();
            return Promise.reject();
        }
        this.data.content = data.content;
        this.data.url = data.url;
        var allWhitespace = /\s+/gi;
        var allStartAndEndSpace = /^\s+|\s+$/gi;
        var allBtnTypes = /(^|[ ])(btn-secondary|btn-success|btn-primary|btn-info|btn-warning|btn-danger)([ ]|$)/gi;
        this.data.classes = data.classes.replace(allWhitespace, ' ').replace(allStartAndEndSpace, '');
        if (data.classes.replace(allBtnTypes, ' ')) {
            this.data.style = {
                'background-color': '',
                'color': '',
            };
        }
        this.data.isNewWindow = data.isNewWindow;
        this.final_data = this.data;
        return Promise.resolve();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
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

        const $linkPreview = this.$("#link-preview");
        $linkPreview.attr(attrs);
        this._updateLinkContent($linkPreview, data, { force: true });
    },
    /**
     * @override
     */
    _doStripDomain: function () {
        return this.$('#o_link_dialog_url_strip_domain').prop('checked');
    },
    /**
     * @override
     */
    _getLinkOptions: function () {
        const options = [
            'input[name="link_style_color"]',
            'select[name="link_style_size"] > option',
            'select[name="link_style_shape"] > option',
        ];
        return this.$(options.join(','));
    },
    /**
     * @override
     */
    _getLinkShape: function () {
        return this.$('select[name="link_style_shape"]').val() || '';
    },
    /**
     * @override
     */
    _getLinkSize: function () {
        return this.$('select[name="link_style_size"]').val() || '';
    },
    /**
     * @override
     */
    _getLinkType: function () {
        return this.$('input[name="link_style_color"]:checked').val() || '';
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
        } catch (_ignored) {
            return true;
        }
    },
    /**
     * @override
     */
    _isNewWindow: function (url) {
        if (this.options.forceNewWindow) {
            return this._isFromAnotherHostName(url);
        } else {
            return this.$('input[name="is_new_window"]').prop('checked');
        }
    },
    /**
     * @override
     */
    _setSelectOption: function ($option, active) {
        if ($option.is("input")) {
            $option.prop("checked", active);
        } else if (active) {
            $option.parent().find('option').removeAttr('selected').removeProp('selected');
            $option.parent().val($option.val());
            $option.attr('selected', 'selected').prop('selected', 'selected');
        }
    },
    /**
     * @override
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
    _onTypeChange() {
        this._updateOptionsUI();
    },
    /**
     * @override
     */
    _onURLInput: function () {
        this._super(...arguments);
        this.$('#o_link_dialog_url_input').closest('.o_url_input').removeClass('o_has_error').find('.form-control, .form-select').removeClass('is-invalid');
    },
});

/**
 * Allows to customize link content and style.
 */
const LinkDialog = Dialog.extend({
    init: function (parent, ...args) {
        this._super(...arguments);
        this.linkWidget = this.getLinkWidget(...args);
    },
    start: async function () {
        const res = await this._super(...arguments);
        await this.linkWidget.appendTo(this.$el);
        return res;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns an instance of the widget that will be attached to the body of the
     * link dialog. One may overwrite this function and return an instance of
     * another widget to change the default logic.
     * @param {...any} args
     */
    getLinkWidget: function (...args) {
        return new _DialogLinkWidget(this, ...args);
    },

    /**
     * @override
     */
    save: function () {
        const _super = this._super.bind(this);
        const saveArguments = arguments;
        return this.linkWidget.save().then(() => {
            this.final_data = this.linkWidget.final_data;
            return _super(...saveArguments);
        });
    },
});

return LinkDialog;
});
