odoo.define('wysiwyg.widgets.LinkTools', function (require) {
'use strict';

const Link = require('wysiwyg.widgets.Link');
const OdooEditorLib = require('web_editor.odoo-editor');

const nodeSize = OdooEditorLib.nodeSize;
const setCursor = OdooEditorLib.setCursor;

/**
 * Allows to customize link content and style.
 */
const LinkTools = Link.extend({
    template: 'wysiwyg.widgets.linkTools',
    events: _.extend({}, Link.prototype.events, {
        'click we-select we-button': '_onPickSelectOption',
        'click we-checkbox': '_onClickCheckbox',
    }),

    /**
     * @override
     */
    init: function (parent, options, editable, data, $button, link) {
        link = link || this.getOrCreateLink(editable);
        this._super(parent, options, editable, data, $button, link);
    },
    /**
     * @override
     */
    start: function () {
        this.options.wysiwyg.odooEditor.observerUnactive();
        this.$link.addClass('oe_edited_link');
        this.$button.addClass('active');
        return this._super(...arguments);
    },
    destroy: function () {
        $('.oe_edited_link').removeClass('oe_edited_link');
        const $contents = this.$link.contents();
        if (!this.$link.attr('href') && !this.colorCombinationClass) {
            $contents.unwrap();
        }
        this.$button.removeClass('active');
        this.options.wysiwyg.odooEditor.observerActive();
        this.applyLinkToDom(this._getData());
        const start = $contents[0] || this.$link[0];
        const end = $contents[$contents.length - 1] || this.$link[0];
        setCursor(start, 0, end, nodeSize(end));
        this.options.wysiwyg.odooEditor.historyStep();
        this._super(...arguments);
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
        data.classes += ' oe_edited_link';
        this.applyLinkToDom(data);
    },
    /**
     * @override
     */
    _doStripDomain: function () {
        return this.$('we-checkbox[name="do_strip_domain"]').closest('we-button.o_we_checkbox_wrapper').hasClass('active');
    },
    /**
     * @override
     */
    _getLinkOptions: function () {
        const options = [
            'we-selection-items[name="link_style_color"] > we-button',
            'we-selection-items[name="link_style_size"] > we-button',
            'we-selection-items[name="link_style_shape"] > we-button',
        ];
        return this.$(options.join(','));
    },
    /**
     * @override
     */
    _getLinkShape: function () {
        return this.$('we-selection-items[name="link_style_shape"] we-button.active').data('value') || '';
    },
    /**
     * @override
     */
    _getLinkSize: function () {
        return this.$('we-selection-items[name="link_style_size"] we-button.active').data('value') || '';
    },
    /**
     * @override
     */
    _getLinkType: function () {
        return this.$('we-selection-items[name="link_style_color"] we-button.active').data('value') || '';
    },
    /**
     * @override
     */
    _isNewWindow: function () {
        return this.$('we-checkbox[name="is_new_window"]').closest('we-button.o_we_checkbox_wrapper').hasClass('active');
    },
    /**
     * @override
     */
    _setSelectOption: function ($option, active) {
        $option.toggleClass('active', active);
        if (active) {
            $option.closest('we-select').find('we-toggler').text($option.text());
            // ensure only one option is active in the dropdown
            $option.siblings('we-button').removeClass("active");
        }
    },
    /**
     * @override
     */
    _updateOptionsUI: function () {
        const el = this.el.querySelector('[name="link_style_color"] we-button.active');
        if (el) {
            this.colorCombinationClass = el.dataset.value;
            // Hide the size and shape options if the link is an unstyled anchor.
            this.$('.link-size-row, .link-shape-row').toggleClass('d-none', !this.colorCombinationClass);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClickCheckbox: function (ev) {
        const $target = $(ev.target);
        $target.closest('we-button.o_we_checkbox_wrapper').toggleClass('active');
        this._adaptPreview();
    },
    _onPickSelectOption: function (ev) {
        const $target = $(ev.target);
        const $select = $target.closest('we-select');
        $select.find('we-selection-items we-button').toggleClass('active', false);
        this._setSelectOption($target, true);
        this._updateOptionsUI();
        this._adaptPreview();
    },
});

return LinkTools;
});
