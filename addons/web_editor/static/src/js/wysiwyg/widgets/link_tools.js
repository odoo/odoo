/** @odoo-module alias=wysiwyg.widgets.LinkTools **/

import Link from "wysiwyg.widgets.Link";
import {ColorPaletteWidget} from "web_editor.ColorPalette";
import {ColorpickerWidget} from "web.Colorpicker";
import {
    computeColorClasses,
    getCSSVariableValue,
    getColorClass,
    getNumericAndUnit,
    isColorGradient,
} from "web_editor.utils";

/**
 * Allows to customize link content and style.
 */
const LinkTools = Link.extend({
    template: 'wysiwyg.widgets.linkTools',
    events: Object.assign({}, Link.prototype.events, {
        'click we-select we-button': '_onPickSelectOption',
        'click we-checkbox': '_onClickCheckbox',
        'change .link-custom-color-border input': '_onChangeCustomBorderWidth',
        'keypress .link-custom-color-border input': '_onKeyPressCustomBorderWidth',
        'click we-select [name="link_border_style"] we-button': '_onBorderStyleSelectOption',
        'input input[name="label"]': '_onLabelInput',
    }),

    /**
     * @override
     */
    init: function (parent, options, editable, data, $button, link) {
        this._link = link;
        this._observer = new MutationObserver(async () => {
            await this.renderingPromise;
            this._updateLabelInput();
        });
        this._observer.observe(this._link, {subtree: true, childList: true, characterData: true});
        this._super(parent, options, editable, data, $button, this._link);
        // Keep track of each selected custom color and colorpicker.
        this.customColors = {};
        this.colorpickers = {};
        this.COLORPICKER_CSS_PROPERTIES = ['color', 'background-color', 'border-color'];
        this.PREFIXES = {
            'color': 'text-',
            'background-color': 'bg-',
        };
    },
    /**
     * @override
     */
    willStart: async function () {
        const _super = this._super.bind(this);
        await Promise.all(this.COLORPICKER_CSS_PROPERTIES.map(cssProperty => this._addColorPicker(cssProperty)));
        return _super(...arguments);
    },
    /**
     * @override
     */
    start: async function () {
        this._addHintClasses();
        const ret = await this._super(...arguments);
        const link = this.$link[0];
        const colorpickerLocations = {
            'color': '.link-custom-color-text .dropdown-menu',
            'background-color': '.link-custom-color-fill .dropdown-menu',
            'border-color': '.link-custom-color-border .o_we_so_color_palette .dropdown-menu',
        };
        for (const cssProperty of this.COLORPICKER_CSS_PROPERTIES) {
            // Colorpickers were created into fragments before any UI or event
            // handler of this main widget was built. This just moves those
            // colorpickers at their rightful position, synchronously.
            const locationEl = this.el.querySelector(colorpickerLocations[cssProperty]);
            this.colorpickers[cssProperty].$el.appendTo(locationEl);
        }
        const customStyleProps = ['color', 'background-color', 'background-image', 'border-width', 'border-style', 'border-color'];
        if (customStyleProps.some(s => link.style[s])) {
            // Force custom style if style exists on the link.
            const customOption = this.el.querySelector('[name="link_style_color"] we-button[data-value="custom"]');
            this._setSelectOption($(customOption), true);
            this._updateOptionsUI();
        }
        return ret;
    },
    destroy: function () {
        if (!this.el) {
            return this._super(...arguments);
        }
        const $contents = this.$link.contents();
        if (this.shouldUnlink()) {
            $contents.unwrap();
        }
        this._observer.disconnect();
        this._super(...arguments);
        this._removeHintClasses();
    },
    shouldUnlink: function () {
        return !this.$link.attr('href') && !this.colorCombinationClass
    },
    applyLinkToDom() {
        this._observer.disconnect();
        this._removeHintClasses();
        this._super(...arguments);
        this.options.wysiwyg.odooEditor.historyStep();
        this._addHintClasses();
        this._observer.observe(this._link, {subtree: true, childList: true, characterData: true});
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    focusUrl() {
        this.el.scrollIntoView();
        this._super();
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
    _getIsNewWindowFormRow() {
        return this.$('we-checkbox[name="is_new_window"]').closest('we-row');
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
        return this.customColors['color'];
    },
    /**
     * @override
     */
    _getLinkCustomBorder: function () {
        return this.customColors['border-color'];
    },
    /**
     * @override
     */
    _getLinkCustomBorderWidth: function () {
        return this.$('.link-custom-color-border input').val() || '';
    },
    /**
     * @override
     */
    _getLinkCustomBorderStyle: function () {
        return this.$('.link-custom-color-border we-button.active').data('value') || '';
    },
    /**
     * @override
     */
    _getLinkCustomFill: function () {
        return this.customColors['background-color'];
    },
    /**
     * @override
     */
    _getLinkCustomClasses: function () {
        let textClass = this.customColors['color'];
        const colorPickerFg = this.colorpickers['color'];
        if (
            !textClass ||
            !colorPickerFg ||
            !computeColorClasses(colorPickerFg.getColorNames(), 'text-').includes(textClass)
        ) {
            textClass = '';
        }
        let fillClass = this.customColors['background-color'];
        const colorPickerBg = this.colorpickers['background-color'];
        if (
            !fillClass ||
            !colorPickerBg ||
            !computeColorClasses(colorPickerBg.getColorNames(), 'bg-').includes(fillClass)
        ) {
            fillClass = '';
        }
        return ` ${textClass} ${fillClass}`;
    },
    /**
     * @override
     */
    _isNewWindow: function (url) {
        if (this.options.forceNewWindow) {
            return this._isFromAnotherHostName(url);
        } else {
            return this.$('we-checkbox[name="is_new_window"]').closest('we-button.o_we_checkbox_wrapper').hasClass('active');
        }
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

            // Note: the _updateColorpicker method is supposedly async but can
            // be used synchronously given the fact that _addColorPicker was
            // called during this widget initialization.
            this._updateColorpicker('color');
            this._updateColorpicker('background-color');
            this._updateColorpicker('border-color');

            const borderWidth = this.linkEl.style['border-width'];
            const numberAndUnit = getNumericAndUnit(borderWidth);
            this.$('.link-custom-color-border input').val(numberAndUnit ? numberAndUnit[0] : "1");
            let borderStyle = this.linkEl.style['border-style'];
            if (!borderStyle || borderStyle === 'none') {
                borderStyle = 'solid';
            }
            const $activeBorderStyleButton = this.$(`.link-custom-color-border [name="link_border_style"] we-button[data-value="${borderStyle}"]`);
            $activeBorderStyleButton.addClass('active');
            $activeBorderStyleButton.siblings('we-button').removeClass("active");
            const $activeBorderStyleToggler = $activeBorderStyleButton.closest('we-select').find('we-toggler');
            $activeBorderStyleToggler.empty();
            $activeBorderStyleButton.find('div').clone().appendTo($activeBorderStyleToggler);
        }
    },
    /**
     * Updates the colorpicker associated to a given property - updated with its selected color.
     *
     * @private
     * @param {string} cssProperty
     */
    _updateColorpicker: async function (cssProperty) {
        const prefix = this.PREFIXES[cssProperty];
        let colorpicker = this.colorpickers[cssProperty];

        // Update selected color.
        const colorNames = colorpicker.getColorNames();
        let color = this.linkEl.style[cssProperty];
        const colorClasses = prefix ? computeColorClasses(colorNames, prefix) : [];
        const colorClass = prefix && getColorClass(this.linkEl, colorNames, prefix);
        const isColorClass = colorClasses.includes(colorClass);
        if (isColorClass) {
            color = colorClass;
        } else if (cssProperty === 'background-color') {
            const gradientColor = this.linkEl.style['background-image'];
            if (isColorGradient(gradientColor)) {
                color = gradientColor;
            }
        }
        this.customColors[cssProperty] = color;
        if (cssProperty === 'border-color') {
            // Highlight matching named color if any.
            const colorName = colorpicker.colorToColorNames[ColorpickerWidget.normalizeCSSColor(color)];
            colorpicker.setSelectedColor(null, colorName || color, false);
        } else {
            colorpicker.setSelectedColor(null, isColorClass ? color.replace(prefix, '') : color, false);
        }

        // Update preview.
        const $colorPreview = this.$('.link-custom-color-' + (cssProperty === 'border-color' ? 'border' : cssProperty === 'color' ? 'text' : 'fill') + ' .o_we_color_preview');
        const previewClasses = computeColorClasses(colorNames, 'bg-');
        $colorPreview[0].classList.remove(...previewClasses);
        if (isColorClass) {
            $colorPreview.css('background-color', `var(--we-cp-${color.replace(prefix, '')}`);
            $colorPreview.css('background-image', '');
        } else {
            $colorPreview.css('background-color', isColorGradient(color) ? 'rgba(0, 0, 0, 0)' : color);
            $colorPreview.css('background-image', isColorGradient(color) ? color : '');
        }
    },
    /**
     * @private
     * @param {string} cssProperty
     */
    async _addColorPicker(cssProperty) {
        const prefix = this.PREFIXES[cssProperty];
        const colorpicker = new ColorPaletteWidget(this, {
            excluded: ['transparent_grayscale'],
            $editable: $(this.options.wysiwyg.odooEditor.editable),
            withGradients: cssProperty === 'background-color',
        });
        this.colorpickers[cssProperty] = colorpicker;
        await colorpicker.appendTo(document.createDocumentFragment());
        colorpicker.on('custom_color_picked color_picked color_hover color_leave', this, (ev) => {
            // Reset color styles in link content to make sure new color is not hidden.
            // Only done when applied to avoid losing state during preview.
            if (['custom_color_picked', 'color_picked'].includes(ev.name)) {
                const selection = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(this.linkEl);
                selection.removeAllRanges();
                selection.addRange(range);
                this.options.wysiwyg.odooEditor.execCommand('applyColor', '', 'color');
                this.options.wysiwyg.odooEditor.execCommand('applyColor', '', 'backgroundColor');
            }

            let color = ev.data.color;
            const colorNames = colorpicker.getColorNames();
            const colorClasses = prefix ? computeColorClasses(colorNames, prefix) : [];
            const colorClass = `${prefix}${color}`;
            if (colorClasses.includes(colorClass)) {
                color = colorClass;
            } else if (colorNames.includes(color)) {
                // Store as color value.
                color = getCSSVariableValue(color);
            }
            this.customColors[cssProperty] = color;
            this.applyLinkToDom(this._getData());
            if (['custom_color_picked', 'color_picked'].includes(ev.name)) {
                this.options.wysiwyg.odooEditor.historyStep();
                this._updateOptionsUI();
            }
        });
        return colorpicker;
    },
    /**
     * Add hint to the classes of the link and button.
     */
    _addHintClasses () {
        this.options.wysiwyg.odooEditor.observerUnactive("hint_classes");
        this.$link.addClass('oe_edited_link');
        this.$button.addClass('active');
        this.options.wysiwyg.odooEditor.observerActive("hint_classes");
    },
    /**
     * Remove hint to the classes of the link and button.
     */
    _removeHintClasses () {
        this.options.wysiwyg.odooEditor.observerUnactive("hint_classes");
        $(this.options.wysiwyg.odooEditor.document).find('.oe_edited_link').removeClass('oe_edited_link');
        this.$button.removeClass('active');
        this.options.wysiwyg.odooEditor.observerActive("hint_classes");
    },
    /**
     * Updates the label input with the DOM content of the link.
     *
     * @private
     */
    _updateLabelInput() {
        this.el.querySelector('#o_link_dialog_label_input').value = this.linkEl.innerText;
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
    /**
     * @override
     */
    __onURLInput() {
        this._super(...arguments);
        this.options.wysiwyg.odooEditor.historyPauseSteps('_onURLInput');
        this._adaptPreview();
        this.options.wysiwyg.odooEditor.historyUnpauseSteps('_onURLInput');
    },
    /**
     * Updates the DOM content of the link with the input value.
     *
     * @private
     * @param {Event} ev
     */
    _onLabelInput(ev) {
        const data = this._getData();
        if (!data) {
            return;
        }
        this._observer.disconnect();
        // Force update of link's content with new data using 'force: true'.
        // Without this, no update if input is same as original text.
        this._updateLinkContent(this.$link, data, {force: true});
        this._observer.observe(this._link, {subtree: true, childList: true, characterData: true});
    },
});

export default LinkTools;
