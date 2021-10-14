odoo.define('wysiwyg.widgets.LinkTools', function (require) {
'use strict';

const Link = require('wysiwyg.widgets.Link');
const {ColorPaletteWidget} = require('web_editor.ColorPalette');
const OdooEditorLib = require('@web_editor/../lib/odoo-editor/src/OdooEditor');
const dom = require('web.dom');
const {getNumericAndUnit, isColorGradient} = require('web_editor.utils');

const setSelection = OdooEditorLib.setSelection;

/**
 * Allows to customize link content and style.
 */
const LinkTools = Link.extend({
    template: 'wysiwyg.widgets.linkTools',
    events: _.extend({}, Link.prototype.events, {
        'click we-select we-button': '_onPickSelectOption',
        'click we-checkbox': '_onClickCheckbox',
        'click .link-custom-color span[data-toggle]': '_onClickCustomColor',
        'change .link-custom-color-border input': '_onChangeCustomBorderWidth',
        'keypress .link-custom-color-border input': '_onKeyPressCustomBorderWidth',
        'click we-select [name="link_border_style"] we-button': '_onBorderStyleSelectOption',
    }),

    /**
     * @override
     */
    init: function (parent, options, editable, data, $button, node) {
        if (node && !$(node).is('a')) {
            $(node).wrap('<a href="#"/>');
            node = node.parentElement;
        }
        const link = node || this.getOrCreateLink(editable);
        this._super(parent, options, editable, data, $button, link);
        // Keep track of each colorpicker.
        this.colorpickers = {};
    },
    /**
     * @override
     */
    start: function () {
        this.options.wysiwyg.odooEditor.observerUnactive();
        this.$link.addClass('oe_edited_link');
        this.$button.addClass('active');
        return this._super(...arguments).then(() => {
            if (!this.options.noFocusUrl) {
                dom.scrollTo(this.$(':visible:last')[0], {duration: 0});
            }
        });
    },
    destroy: function () {
        if (!this.el) {
            return this._super(...arguments);
        }
        this.$link.removeClass('oe_edited_link');
        const $contents = this.$link.contents();
        if (!this.$link.attr('href') && !this.colorCombinationClass) {
            $contents.unwrap();
        }
        this.$button.removeClass('active');
        this.options.wysiwyg.odooEditor.observerActive();
        this.applyLinkToDom(this._getData());
        setSelection(this.$link[0], 0, this.$link[0], 1);
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
    _getLinkCustomTextColor: function () {
        return this.$('we-selection-items[name="link-custom-color-text"] .o_we_color_preview').css('background-color') || '';
    },
    /**
     * @override
     */
    _getLinkCustomBorder: function () {
        return this.$('we-selection-items[name="link_border_color"] .o_we_color_preview').css('background-color') || '';
    },
    /**
     * @override
     */
    _getLinkCustomBorderWidth: function () {
        return this.$('we-selection-items[name="link_border_color"] input').val() || '';
    },
    /**
     * @override
     */
    _getLinkCustomBorderStyle: function () {
        return this.$('we-selection-items[name="link_border_style"] we-button.active').data('value') || '';
    },
    /**
     * @override
     */
    _getLinkCustomFill: function () {
        const $colorPreview = this.$('we-selection-items[name="link-custom-color-fill"] .o_we_color_preview');
        return $colorPreview.css('background-image') || $colorPreview.css('background-color') || '';
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
            // Show custom colors only for Custom style.
            this.$('.link-custom-color').toggleClass('d-none', el.dataset.value !== 'custom');
            if (el.dataset.value === 'custom') {
                const textColor = this.$link[0].style['color'];
                this.$('.link-custom-color-text .o_we_color_preview').css('background-color', textColor);
                if (this.colorpickers['color'] && textColor && textColor !== 'false') {
                    // Keep currently selected tab when setting color.
                    this.colorpickers['color'].setSelectedColor(null, textColor, false);
                }
                const backgroundColor = this.$link[0].style['background-color'];
                this.$('.link-custom-color-fill .o_we_color_preview').css('background-color', backgroundColor);
                const backgroundImage = this.$link[0].style['background-image'];
                this.$('.link-custom-color-fill .o_we_color_preview').css('background-image', backgroundImage);
                const backgroundFill = (backgroundImage !== 'false' && backgroundImage) || backgroundColor;
                if (this.colorpickers['background-color'] && backgroundFill && backgroundFill !== 'false') {
                    // Keep currently selected tab when setting color.
                    this.colorpickers['background-color'].setSelectedColor(null, backgroundFill, false);
                }
                const borderWidth = this.$link[0].style['border-width'];
                const numberAndUnit = getNumericAndUnit(borderWidth);
                this.$('.link-custom-color-border input').val(numberAndUnit ? numberAndUnit[0] : "1");
                let borderStyle = this.$link[0].style['border-style'];
                if (!borderStyle || borderStyle === 'none') {
                    borderStyle = 'solid';
                }
                const $activeBorderStyleButton = this.$(`.link-custom-color-border [name="link_border_style"] we-button[data-value="${borderStyle}"]`);
                $activeBorderStyleButton.addClass('active');
                $activeBorderStyleButton.siblings('we-button').removeClass("active");
                const $activeBorderStyleToggler = $activeBorderStyleButton.closest('we-select').find('we-toggler');
                $activeBorderStyleToggler.empty();
                $activeBorderStyleButton.find('div').clone().appendTo($activeBorderStyleToggler);
                const borderColor = this.$link[0].style['border-color'];
                this.$('.link-custom-color-border .o_we_color_preview').css('background-color', borderColor);
                if (this.colorpickers['border-color'] && borderColor && borderColor !== 'false') {
                    // Keep currently selected tab when setting color.
                    this.colorpickers['border-color'].setSelectedColor(null, borderColor, false);
                }
            }
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
        if ($target.closest('[name="link_border_style"]').length) {
            return;
        }
        const $select = $target.closest('we-select');
        $select.find('we-selection-items we-button').toggleClass('active', false);
        this._setSelectOption($target, true);
        this._updateOptionsUI();
        this._adaptPreview();
    },
    /**
     * Sets the color on the link.
     *
     * @private
     * @param {Event} ev
     */
    _onClickCustomColor: function (ev) {
        const cssProperty = ev.target.dataset.cssProperty;
        let color = this.$link.css(cssProperty);
        if (cssProperty === 'background-color') {
            const gradientColor = this.$link.css('background-image');
            if (isColorGradient(gradientColor)) {
                color = gradientColor;
            }
        }
        const colorpicker = new ColorPaletteWidget(this, {
            excluded: ['transparent_grayscale'],
            $editable: $(this.options.wysiwyg.odooEditor.editable),
            selectedColor: color,
            withGradients: cssProperty === 'background-color',
        });
        this.colorpickers[cssProperty] = colorpicker;
        colorpicker.appendTo($(ev.target).closest('.dropdown').find('.dropdown-menu'));
        colorpicker.on('custom_color_picked color_picked color_hover color_leave', this, (ev) => {
            let color = ev.data.color;
            let gradientColor = '';
            if (cssProperty === 'background-color') {
                if (isColorGradient(color)) {
                    gradientColor = color;
                    color = 'rgba(0, 0, 0, 0)';
                }
                this.$link.css('background-image', gradientColor);
            }
            this.$link.css(cssProperty, color);
            if (['custom_color_picked', 'color_picked'].includes(ev.name)) {
                const $colorPreview = this.$('.link-custom-color-' + (cssProperty === 'border-color' ? 'border' : cssProperty === 'color' ? 'text' : 'fill') + ' .o_we_color_preview');
                $colorPreview.css('background-color', color);
                $colorPreview.css('background-image', gradientColor);
                this.options.wysiwyg.odooEditor.historyStep();
                this._updateOptionsUI();
            }
        });
    },
    /**
     * Sets the border width on the link.
     *
     * @private
     * @param {Event} ev
     */
    _onChangeCustomBorderWidth: function (ev) {
        const value = ev.target.value;
        if (parseInt(value) >= 0) {
            this.$link.css('border-width', value + 'px');
        }
    },
    /**
     * Sets the border width on the link when enter is pressed.
     *
     * @private
     * @param {Event} ev
     */
    _onKeyPressCustomBorderWidth: function (ev) {
        if (ev.keyCode === $.ui.keyCode.ENTER) {
            this._onChangeCustomBorderWidth(ev);
        }
    },
    /**
     * Sets the border style on the link.
     *
     * @private
     * @param {Event} ev
     */
    _onBorderStyleSelectOption: function (ev) {
        const value = ev.currentTarget.dataset.value;
        if (value) {
            this.$link.css('border-style', value);
            const $target = $(ev.currentTarget);
            const $activeBorderStyleToggler = $target.closest('we-select').find('we-toggler');
            $activeBorderStyleToggler.empty();
            $target.find('div').clone().appendTo($activeBorderStyleToggler);
            // Ensure only one option is active in the dropdown.
            $target.addClass('active');
            $target.siblings('we-button').removeClass("active");
            this.options.wysiwyg.odooEditor.historyStep();
        }
    },
});

return LinkTools;
});
