odoo.define('web_editor.ColorPalette', function (require) {
'use strict';

const ajax = require('web.ajax');
const core = require('web.core');
const session = require('web.session');
const {ColorpickerWidget} = require('web.Colorpicker');
const Widget = require('web.Widget');
const customColors = require('web_editor.custom_colors');
const weUtils = require('web_editor.utils');

const qweb = core.qweb;

let colorpickerArch;

const ColorPaletteWidget = Widget.extend({
    // ! for xmlDependencies, see loadDependencies function
    template: 'web_editor.snippet.option.colorpicker',
    events: {
        'click .o_we_color_btn': '_onColorButtonClick',
        'mouseenter .o_we_color_btn': '_onColorButtonEnter',
        'mouseleave .o_we_color_btn': '_onColorButtonLeave',
        'click .o_we_colorpicker_switch_pane_btn': '_onSwitchPaneButtonClick',
        'click .o_custom_gradient_editor .o_custom_gradient_btn': '_onGradientCustomButtonClick',
        'click .o_custom_gradient_editor': '_onPanelClick',
        'change .o_custom_gradient_editor input[type="text"]': '_onGradientInputChange',
        'keypress .o_custom_gradient_editor input[type="text"]': '_onGradientInputKeyPress',
        'click .o_custom_gradient_editor we-button:not(.o_remove_color)': '_onGradientButtonClick',
        'mouseenter .o_custom_gradient_editor we-button:not(.o_remove_color)': '_onGradientButtonEnter',
        'mouseleave .o_custom_gradient_editor we-button:not(.o_remove_color)': '_onGradientButtonLeave',
        'click .o_custom_gradient_scale': '_onGradientPreviewClick',
        // Note: _onGradientSliderClick on slider is attached at slider creation.
        'click .o_custom_gradient_editor .o_remove_color': '_onGradientDeleteClick',
    },
    custom_events: {
        'colorpicker_select': '_onColorPickerSelect',
        'colorpicker_preview': '_onColorPickerPreview',
    },
    /**
     * @override
     *
     * @param {Object} [options]
     * @param {string} [options.selectedColor] The class or css attribute color selected by default.
     * @param {boolean} [options.resetButton=true] Whether to display or not the reset button.
     * @param {string[]} [options.excluded=[]] Sections not to display.
     * @param {string[]} [options.excludeSectionOf] Extra section to exclude: the one containing the named color.
     * @param {boolean} [options.withCombinations=false] Enable color combinations selection.
     * @param {float} [options.noTransparency=false] Specify a default opacity (predefined gradients & color).
     * @param {float} [options.opacity=1] Specify a default opacity (predefined gradients & color).
     * @param {string} [options.selectedTab='theme-colors'] Tab initially selected.
     * @param {boolean} [options.withGradients=false] Enable gradient selection.
     * @param {JQuery} [options.$editable=$()] Editable content from which the custom colors are retrieved.
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.style = window.getComputedStyle(document.documentElement);
        this.options = _.extend({
            selectedColor: false,
            resetButton: true,
            excluded: [],
            excludeSectionOf: null,
            $editable: $(),
            withCombinations: false,
            noTransparency: false,
            opacity: 1,
            selectedTab: 'theme-colors',
            withGradients: false,
        }, options || {});
        this.selectedColor = '';
        this.resetButton = this.options.resetButton;
        this.withCombinations = this.options.withCombinations;

        this.trigger_up('request_editable', {callback: val => this.options.$editable = val});

        this.tabs = [{
            id: 'theme-colors',
            pickers: [
                'theme',
                'common',
            ],
        },
        {
            id: 'custom-colors',
            pickers: [
                'custom',
                'transparent_grayscale',
                'common_grays',
            ],
        },
        {
            id: 'gradients',
            pickers: this.options.withGradients ? [
                'predefined_gradients',
                'custom_gradient',
            ] : [],
        }];

        this.sections = {};
        this.pickers = {};
    },
    /**
     * @override
     */
    willStart: async function () {
        await this._super(...arguments);
        await ColorPaletteWidget.loadDependencies(this);
    },
    /**
     * @override
     */
    start: async function () {
        const res = this._super.apply(this, arguments);

        const switchPaneButtons = this.el.querySelectorAll('.o_we_colorpicker_switch_pane_btn');

        let colorpickerEl;
        if (colorpickerArch) {
            colorpickerEl = $(colorpickerArch)[0];
        } else {
            colorpickerEl = document.createElement("colorpicker");
            const sectionEl = document.createElement('DIV');
            sectionEl.classList.add('o_colorpicker_section');
            sectionEl.dataset.name = 'common';
            colorpickerEl.appendChild(sectionEl);
        }
        colorpickerEl.querySelectorAll('button').forEach(el => el.classList.add('o_we_color_btn'));

        // Populate tabs based on the tabs configuration indicated in this.tabs
        _.each(this.tabs, (tab, index) => {
            // Append pickers to section
            const sectionEl = this.el.querySelector(`.o_colorpicker_sections[data-color-tab="${tab.id}"]`);
            let sectionIsEmpty = true;
            _.each(tab.pickers, pickerId => {
                let pickerEl;
                switch (pickerId) {
                    case 'common_grays':
                        pickerEl = colorpickerEl.querySelector('[data-name="common"]').cloneNode(true);
                        break;
                    case 'custom':
                        pickerEl = document.createElement('DIV');
                        pickerEl.classList.add("o_colorpicker_section");
                        pickerEl.dataset.name = 'custom';
                        break;
                    default:
                        pickerEl = colorpickerEl.querySelector(`[data-name="${pickerId}"]`);
                        pickerEl = pickerEl && pickerEl.cloneNode(true);
                }
                if (pickerEl) {
                    sectionEl.appendChild(pickerEl);

                    if (!this.options.excluded.includes(pickerId)) {
                        sectionIsEmpty = false;
                    }

                    this.pickers[pickerId] = pickerEl;
                }
            });

            // If the section is empty, hide it and
            // select the next tab if none is given in the options
            if (sectionIsEmpty) {
                sectionEl.classList.add('d-none');
                switchPaneButtons[index].classList.add('d-none');
                if (this.options.selectedTab === tab.id) {
                    this.options.selectedTab = this.tabs[(index + 1) % this.tabs.length].id;
                }
            }
            this.sections[tab.id] = sectionEl;
        });

        // Predefined gradient opacity
        if (this.options.withGradients && this.options.opacity !== 1) {
            this.pickers['predefined_gradients'].querySelectorAll('button').forEach(elem => {
                let gradient = elem.dataset.color;
                gradient = gradient.replaceAll(/rgba?(\(\s*\d+\s*,\s*\d+\s*,\s*\d+)(?:\s*,.+?)?\)/g,
                    `rgba$1, ${this.options.opacity})`);
                elem.dataset.color = gradient.replaceAll(/\s+/g, '');
            });
        }

        // Palette for gradient
        if (this.pickers['custom_gradient']) {
            this.gradientColorPicker = new ColorpickerWidget(this, {
                stopClickPropagation: true,
            });
            await this.gradientColorPicker.appendTo(this.sections['gradients']);
            const editor = this.pickers['custom_gradient'];
            this.gradientEditorParts = {
                'customButton': editor.querySelector('.o_custom_gradient_btn'),
                'customContent': editor.querySelector('.o_color_picker_inputs'),
                'linearButton': editor.querySelector('we-button[data-gradient-type="linear-gradient"]'),
                'angleRow': editor.querySelector('.o_angle_row'),
                'angle': editor.querySelector('input[data-name="angle"]'),
                'radialButton': editor.querySelector('we-button[data-gradient-type="radial-gradient"]'),
                'positionRow': editor.querySelector('.o_position_row'),
                'positionX': editor.querySelector('input[data-name="positionX"]'),
                'positionY': editor.querySelector('input[data-name="positionY"]'),
                'sizeRow': editor.querySelector('.o_size_row'),
                'scale': editor.querySelector('.o_custom_gradient_scale div'),
                'sliders': editor.querySelector('.o_slider_multi'),
                'deleteButton': editor.querySelector('.o_remove_color'),
            };
            const gradient = weUtils.isColorGradient(this.options.selectedColor) && this.options.selectedColor;
            this._selectGradient(gradient);
            const resizeObserver = new window.ResizeObserver(() => {
                this._adjustActiveSliderDelete();
            });
            resizeObserver.observe(this.gradientEditorParts.sliders);
        }

        // Switch to the correct tab
        const selectedButtonIndex = this.tabs.map(tab => tab.id).indexOf(this.options.selectedTab);
        this._selectTabFromButton(this.el.querySelectorAll('button')[selectedButtonIndex]);

        // Remove the buttons display if there is only one
        const visibleButtons = Array.from(switchPaneButtons).filter(button => !button.classList.contains('d-none'));
        if (visibleButtons.length === 1) {
            visibleButtons[0].classList.add('d-none');
        }

        // Remove excluded palettes (note: only hide them to still be able
        // to remove their related colors on the DOM target)
        _.each(this.options.excluded, exc => {
            this.$('[data-name="' + exc + '"]').addClass('d-none');
        });
        if (this.options.excludeSectionOf) {
            this.$('[data-name]:has([data-color="' + this.options.excludeSectionOf + '"])').addClass('d-none');
        }

        this.el.querySelectorAll('.o_colorpicker_section').forEach(elem => {
            $(elem).prepend('<div>' + (elem.dataset.display || '') + '</div>');
        });

        // Render common colors
        if (!this.options.excluded.includes('common')) {
            customColors.forEach((colorRow, i) => {
                if (i === 0) {
                    return; // Ignore the wysiwyg gray palette and use ours
                }
                const $div = $('<div/>', {class: 'clearfix'}).appendTo(this.pickers['common']);
                colorRow.forEach(color => {
                    $div.append(this._createColorButton(color, ['o_common_color']));
                });
            });
        }

        // Compute class colors
        const compatibilityColorNames = ['primary', 'secondary', 'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'success', 'info', 'warning', 'danger'];
        this.colorNames = [...compatibilityColorNames];
        this.colorToColorNames = {};
        this.el.querySelectorAll('button[data-color]:not(.o_custom_gradient_btn)').forEach(elem => {
            const colorName = elem.dataset.color;
            if (weUtils.isColorGradient(colorName)) {
                return;
            }
            const $color = $(elem);
            const isCCName = weUtils.isColorCombinationName(colorName);
            if (isCCName) {
                $color.find('.o_we_cc_preview_wrapper').addClass(`o_cc o_cc${colorName}`);
            } else {
                $color.addClass(`bg-${colorName}`);
            }
            this.colorNames.push(colorName);
            if (!isCCName && !elem.classList.contains('d-none')) {
                const color = weUtils.getCSSVariableValue(colorName, this.style);
                this.colorToColorNames[color] = colorName;
            }
        });

        // Select selected Color and build customColors.
        // If no color is selected selectedColor is an empty string (transparent is interpreted as no color)
        if (this.options.selectedCC) {
            this.selectedCC = this.options.selectedCC;
        }
        if (this.options.selectedColor) {
            let selectedColor = this.options.selectedColor;
            if (compatibilityColorNames.includes(selectedColor)) {
                selectedColor = weUtils.getCSSVariableValue(selectedColor, this.style) || selectedColor;
            }
            selectedColor = ColorpickerWidget.normalizeCSSColor(selectedColor);
            if (selectedColor !== 'rgba(0, 0, 0, 0)') {
                this.selectedColor = this.colorToColorNames[selectedColor] || selectedColor;
            }
        }
        this._buildCustomColors();
        this._markSelectedColor();

        // Colorpicker
        if (!this.options.excluded.includes('custom')) {
            let defaultColor = this.selectedColor;
            if (defaultColor && !ColorpickerWidget.isCSSColor(defaultColor)) {
                defaultColor = weUtils.getCSSVariableValue(defaultColor, this.style);
            }
            if (!defaultColor && this.options.opacity !== 1) {
                defaultColor = 'rgba(0, 0, 0, ' + this.options.opacity + ')';
            }
            this.colorPicker = new ColorpickerWidget(this, {
                defaultColor: defaultColor,
                noTransparency: !!this.options.noTransparency,
            });
            await this.colorPicker.appendTo(this.sections['custom-colors']);
        }
        return res;
    },
    /**
     * Return a list of the color names used in the color palette
     */
    getColorNames: function () {
        return this.colorNames;
    },
    /**
     * Gets the currently selected colors.
     *
     * @returns {Object} ccValue and color (plain color or gradient).
     */
    getSelectedColors() {
        return {
            ccValue: this.selectedCC,
            color: this.selectedColor,
        };
    },
    /**
     * Sets the currently selected colors.
     *
     * Note: the tab selection is done here because of an optimization to avoid creating the whole
     * palette hundreds of times when opening the THEME tab.
     *
     * @param {string|number} ccValue
     * @param {string} color rgb[a]
     * @param {boolean} [selectTab=true]
     */
    setSelectedColor: function (ccValue, color, selectTab = true) {
        if (color === 'rgba(0, 0, 0, 0)' && this.options.opacity !== 1) {
            color = 'rgba(0, 0, 0, ' + this.options.opacity + ')';
        }
        this._selectColor({
            ccValue: ccValue,
            color: color,
        });
        if (selectTab) {
            // This is called on open, restore default tab selection
            const selectedButtonIndex = this.tabs.map(tab => tab.id).indexOf(this.options.selectedTab);
            this._selectTabFromButton(this.el.querySelectorAll('button')[selectedButtonIndex]);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _buildCustomColors: function () {
        if (this.options.excluded.includes('custom')) {
            return;
        }
        this.el.querySelectorAll('.o_custom_color').forEach(el => el.remove());
        const existingColors = new Set(Object.keys(this.colorToColorNames));
        this.trigger_up('get_custom_colors', {
            onSuccess: (colors) => {
                colors.forEach(color => {
                    this._addCustomColor(existingColors, color);
                });
            },
        });
        weUtils.getCSSVariableValue('custom-colors', this.style).split(' ').forEach(v => {
            const color = weUtils.getCSSVariableValue(v.substring(1, v.length - 1), this.style);
            if (ColorpickerWidget.isCSSColor(color)) {
                this._addCustomColor(existingColors, color);
            }
        });
        _.each(this.options.$editable.find('[style*="color"]'), el => {
            for (const colorProp of ['color', 'backgroundColor']) {
                this._addCustomColor(existingColors, el.style[colorProp]);
            }
        });
        if (this.selectedColor) {
            this._addCustomColor(existingColors, this.selectedColor);
        }
    },
    /**
     * Add the color to the custom color section if it is not in the existingColors.
     *
     * @param {string[]} existingColors Colors currently in the colorpicker
     * @param {string} color Color to add to the cuustom colors
     */
    _addCustomColor: function (existingColors, color) {
        if (!color) {
            return;
        }
        if (!ColorpickerWidget.isCSSColor(color)) {
            color = weUtils.getCSSVariableValue(color, this.style);
        }
        const normColor = ColorpickerWidget.normalizeCSSColor(color);
        if (!existingColors.has(normColor)) {
            this._addCustomColorButton(normColor);
            existingColors.add(normColor);
        }
    },
    /**
     * Add a custom button in the coresponding section.
     *
     * @private
     * @param {string} color
     * @param {string[]} classes - classes added to the button
     * @returns {jQuery}
     */
    _addCustomColorButton: function (color, classes = []) {
        classes.push('o_custom_color');
        const $button = this._createColorButton(color, classes);
        return $button.appendTo(this.pickers['custom']);
    },
    /**
     * Return a color button.
     *
     * @param {string} color
     * @param {string[]} classes - classes added to the button
     * @returns {jQuery}
     */
    _createColorButton: function (color, classes) {
        return $('<button/>', {
            class: 'o_we_color_btn ' + classes.join(' '),
            style: 'background-color:' + color + ';',
        });
    },
    /**
     * Gets normalized information about a color button.
     *
     * @private
     * @param {HTMLElement} buttonEl
     * @returns {Object}
     */
    _getButtonInfo: function (buttonEl) {
        const bgColor = buttonEl.style.backgroundColor;
        const value = buttonEl.dataset.color || (bgColor && bgColor !== 'initial' ? ColorpickerWidget.normalizeCSSColor(bgColor) : '') || '';
        const info = {
            target: buttonEl,
        };
        if (!value) {
            info.ccValue = '';
            info.color = '';
        } else if (weUtils.isColorCombinationName(value)) {
            info.ccValue = value;
        } else {
            info.color = value;
        }
        return info;
    },
    /**
     * Set the selectedColor and trigger an event
     *
     * @param {Object} colorInfo
     * @param {string} [colorInfo.ccValue]
     * @param {string} [colorInfo.color]
     * @param {string} [eventName]
     */
    _selectColor: function (colorInfo, eventName) {
        this.selectedCC = colorInfo.ccValue;
        this.selectedColor = colorInfo.color = this.colorToColorNames[colorInfo.color] || colorInfo.color;
        if (eventName) {
            this.trigger_up(eventName, colorInfo);
        }
        this._buildCustomColors();
        if (this.colorPicker) {
            this.colorPicker.setSelectedColor(colorInfo.color);
        }
        if (this.gradientColorPicker) {
            const customGradient = weUtils.isColorGradient(colorInfo.color) ? colorInfo.color : false;
            this._selectGradient(customGradient);
        }
        this._markSelectedColor();
    },
    /**
     * Populates the gradient editor.
     *
     * @private
     * @param {string} gradient CSS string
     */
    _selectGradient: function (gradient) {
        const editor = this.gradientEditorParts;
        if (this.gradientColorPicker.$el) {
            this.gradientColorPicker.do_hide();
        }
        const colorSplits = [];
        if (gradient) {
            gradient = gradient.toLowerCase();
            // Extract colors and their positions: colors can either be in the #rrggbb format or in the
            // rgb/rgba(...) format, positions are expected to be expressed as percentages
            // (lengths are not supported).
            for (const entry of gradient.matchAll(/(#[0-9a-f]{6}|rgba?\(\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*[,\s*[0-9.]*]?\s*\))\s*([[0-9]+%]?)/g)) {
                colorSplits.push([entry[1], entry[2].replace('%', '')]);
            }
        }
        // Consider unsupported gradients as not gradients.
        if (!gradient || colorSplits.length < 2) {
            $(editor.customContent).addClass('d-none');
            editor.customButton.style['background-image'] = '';
            editor.customButton.dataset.color = false;
            return;
        }
        $(editor.customContent).removeClass('d-none');
        editor.customButton.style['background-image'] = gradient;
        editor.customButton.dataset.color = gradient;
        // The scale display shows the gradient colors horizontally by canceling the type and angle
        // which are before the first comma.
        const scaleGradient = gradient.replace(/[^,]+,/, 'linear-gradient(90deg,');
        editor.scale.style['background-image'] = scaleGradient;

        const isLinear = gradient.startsWith('linear-gradient(');
        // Keep track of last selected slider's position.
        let lastSliderPosition;
        const activeSlider = editor.sliders.querySelector('input.active');
        if (activeSlider) {
            lastSliderPosition = activeSlider.value;
        }
        let $lastSlider;
        // Rebuild sliders for each color milestone of the gradient.
        editor.sliders.replaceChildren();
        for (const index in colorSplits) {
            const colorSplit = colorSplits[index];
            let color = colorSplit[0];
            const position = colorSplit[1] || 100 * index / colorSplits.length;
            const $slider = this._createGradientSlider(position, color);
            if (position === lastSliderPosition) {
                $lastSlider = $slider;
            }
        }

        editor.deleteButton.classList.add('d-none');
        // Update form elements related to type.
        if (isLinear) {
            editor.linearButton.classList.add('active');
            editor.radialButton.classList.remove('active');

            let angle = gradient.match(/([0-9]+)deg/);
            angle = angle ? angle[1] : 0;
            editor.angle.value = angle;
        } else {
            editor.linearButton.classList.remove('active');
            editor.radialButton.classList.add('active');

            const sizeMatch = gradient.match(/(closest|farthest)-(side|corner)/);
            const size = sizeMatch ? sizeMatch[0] : 'farthest-corner';
            const $buttons = $(editor.sizeRow).find('we-button');
            $buttons.removeClass('active');
            $(editor.sizeRow).find("we-button[data-gradient-size='" + size + "']").addClass('active');

            const position = gradient.match(/ at ([0-9]+)% ([0-9]+)%/) || ['', '50', '50'];
            editor.positionX.value = position[1];
            editor.positionY.value = position[2];
        }
        this._updateGradientVisibility(isLinear);
        this._activateGradientSlider($lastSlider || $(this.pickers['custom_gradient'].querySelector('.o_slider_multi input')));
    },
    /**
     * Adjusts the visibility of the gradient editor elements.
     *
     * @private
     * @param {boolean} isLinear
     */
    _updateGradientVisibility: function (isLinear) {
        const editor = this.gradientEditorParts;
        if (isLinear) {
            editor.angleRow.classList.remove('d-none');
            editor.angleRow.classList.add('d-flex');
            editor.positionRow.classList.add('d-none');
            editor.positionRow.classList.remove('d-flex');
            editor.sizeRow.classList.add('d-none');
            editor.sizeRow.classList.remove('d-flex');
        } else {
            editor.angleRow.classList.add('d-none');
            editor.angleRow.classList.remove('d-flex');
            editor.positionRow.classList.remove('d-none');
            editor.positionRow.classList.add('d-flex');
            editor.sizeRow.classList.remove('d-none');
            editor.sizeRow.classList.add('d-flex');
        }
    },
    /**
     * Removes the transparency from an rgba color.
     *
     * @private
     * @param {string} color rgba CSS color string
     * @returns {string} rgb CSS color string
     */
    _opacifyColor: function (color) {
        if (color.startsWith('rgba')) {
            return color.replace('rgba', 'rgb').replace(/,\s*[0-9.]+\s*\)/, ')');
        }
        return color;
    },
    /**
     * Creates and adds a slider for the gradient color definition.
     *
     * @private
     * @param {int} position between 0 and 100
     * @param {string} color
     * @returns {jQuery} created slider
     */
    _createGradientSlider: function (position, color) {
        const $slider = $('<input class="w-100" type="range" min="0" max="100"/>');
        $slider.attr('value', position);
        $slider.attr('data-color', color);
        $slider.css('color', this._opacifyColor(color));
        $slider.on('click', this._onGradientSliderClick.bind(this));
        $slider.appendTo(this.gradientEditorParts.sliders);
        this._sortGradientSliders();
        return $slider;
    },
    /**
     * Activates a slider of the gradient color definition.
     *
     * @private
     * @param {jQuery} $slider
     */
    _activateGradientSlider: function ($slider) {
        const $sliders = $(this.gradientEditorParts.sliders).find('input');
        $sliders.removeClass('active');
        $slider.addClass('active');

        const color = $slider.data('color');
        // Note: show before marking the selected color as, unfortunately,
        // setting the color and updating the UI accordinly relies on the widget
        // already being rendered in the DOM.
        this.gradientColorPicker.do_show();
        this.gradientColorPicker.setSelectedColor(color);
        this._sortGradientSliders();
        this._adjustActiveSliderDelete();
    },
    /**
     * Adjusts the position of the slider delete button.
     *
     * @private
     */
    _adjustActiveSliderDelete: function () {
        const $sliders = $(this.gradientEditorParts.sliders).find('input');
        const $activeSlider = $(this.gradientEditorParts.sliders).find('input.active');
        if ($sliders.length > 2 && $activeSlider.length) {
            this.gradientEditorParts.deleteButton.classList.remove('d-none');
            const sliderWidth = $activeSlider.width();
            const thumbWidth = 12; // TODO find a way to access it in CSS
            const deleteWidth = $(this.gradientEditorParts.deleteButton).width();
            const pixelOffset = (sliderWidth - thumbWidth) * $activeSlider[0].value / 100 + (thumbWidth - deleteWidth) / 2;
            this.gradientEditorParts.deleteButton.style['margin-left'] = `${pixelOffset}px`;
            this.gradientEditorParts.deleteButton.style['margin-right'] = `-${deleteWidth / 2}px`;
        } else {
            this.gradientEditorParts.deleteButton.classList.add('d-none');
        }
    },
    /**
     * Reorders the sliders of the gradient color definition by their position.
     *
     * @private
     */
    _sortGradientSliders: function () {
        const $sliderInputs = $(this.gradientEditorParts.sliders).find('input');
        for (const slider of $sliderInputs.sort((a, b) => parseInt(a.value, 10) - parseInt(b.value, 10))) {
            this.gradientEditorParts.sliders.appendChild(slider);
        }
    },
    /**
     * Computes the customized gradient from the custom gradient editor.
     *
     * @private
     * @returns {string} gradient string corresponding to the currently selected options.
     */
    _computeGradient: function () {
        const editor = this.gradientEditorParts;

        const $picker = $(this.pickers['custom_gradient']);

        const colors = [];
        for (const slider of $(editor.sliders).find('input')) {
            const color = ColorpickerWidget.convertCSSColorToRgba($(slider).data('color'));
            const colorText = color.opacity !== 100 ? `rgba(${color.red}, ${color.green}, ${color.blue}, ${color.opacity / 100})`
                : `rgb(${color.red}, ${color.green}, ${color.blue})`;
            const position = slider.value;
            colors.push(`${colorText} ${position}%`);
        }

        const type = $picker.find('.o_type_row we-button.active').data('gradientType');
        const isLinear = type === 'linear-gradient';
        let typeParam;
        if (isLinear) {
            const angle = editor.angle.value || 0;
            typeParam = `${angle}deg`;
        } else {
            const positionX = editor.positionX.value || 50;
            const positionY = editor.positionY.value || 50;
            const size = $picker.find('.o_size_row we-button.active').data('gradientSize');
            typeParam = `circle ${size} at ${positionX}% ${positionY}%`;
        }

        return `${type}(${typeParam}, ${colors.join(', ')})`;
    },
    /**
     * Computes the customized gradient from the custom gradient editor and displays it.
     *
     * @private
     * @param {boolean} isPreview
     */
    _updateGradient: function (isPreview) {
        const gradient = this._computeGradient();
        // Avoid updating an unchanged gradient.
        if (weUtils.areCssValuesEqual(gradient, this.selectedColor) && !isPreview) {
            return;
        }
        this.trigger_up(isPreview ? 'color_hover' : 'color_picked', Object.assign(this.getSelectedColors(), {
            color: gradient,
            target: this.colorPicker.el,
        }));
    },
    /**
     * Marks the selected colors.
     *
     * @private
     */
    _markSelectedColor: function () {
        for (const buttonEl of this.el.querySelectorAll('button')) {
            // TODO buttons should only be search by data-color value
            // instead of style but seems necessary for custom colors right
            // now...
            const value = buttonEl.dataset.color || buttonEl.style.backgroundColor;
            buttonEl.classList.toggle('selected', value
                && (this.selectedCC === value || weUtils.areCssValuesEqual(this.selectedColor, value)));
        }
    },
    /**
     * Display button element as selected
     *
     * @private
     * @param {HTMLElement} buttonEl
     */
    _selectTabFromButton(buttonEl) {
        this.el.querySelectorAll('.o_we_colorpicker_switch_pane_btn').forEach(el => {
            el.classList.remove('active');
        });
        buttonEl.classList.add('active');
        this.el.querySelectorAll('.o_colorpicker_sections').forEach(el => {
            el.classList.toggle('d-none', el.dataset.colorTab !== buttonEl.dataset.target);
        });
    },
    /**
     * Updates a gradient color from a selection in the color picker.
     *
     * @private
     * @param {Event} ev from gradient's colorpicker
     * @param {boolean} isPreview
     */
    _updateGradientColor(ev, isPreview) {
        ev.stopPropagation();
        const $slider = $(this.gradientEditorParts.sliders).find('input.active');
        const color = ev.data.cssColor;
        if (!weUtils.areCssValuesEqual(color, $slider.data('color'))) {
            const previousColor = $slider.data('color');
            $slider.data('color', color);
            this._updateGradient(isPreview);
            if (isPreview) {
                $slider.data('color', previousColor);
            }
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a color button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonClick: function (ev) {
        const buttonEl = ev.currentTarget;
        const colorInfo = Object.assign(this.getSelectedColors(), this._getButtonInfo(buttonEl));
        this._selectColor(colorInfo, 'color_picked');
    },
    /**
     * Called when a color button is entered.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonEnter: function (ev) {
        ev.stopPropagation();
        this.trigger_up('color_hover', Object.assign(this.getSelectedColors(), this._getButtonInfo(ev.currentTarget)));
    },
    /**
     * Called when a color button is left the data color is the color currently selected.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonLeave: function (ev) {
        ev.stopPropagation();
        this.trigger_up('color_leave', Object.assign(this.getSelectedColors(), {
            target: ev.target,
        }));
    },
    /**
     * Called when an update is made on the colorpicker.
     *
     * @private
     * @param {Event} ev
     */
    _onColorPickerPreview: function (ev) {
        if (ev.target === this.gradientColorPicker) {
            this._updateGradientColor(ev, true);
        } else {
            this.trigger_up('color_hover', Object.assign(this.getSelectedColors(), {
                color: ev.data.cssColor,
                target: this.colorPicker.el,
            }));
        }
    },
    /**
     * Called when a color is selected on the colorpicker (mouseup).
     *
     * @private
     * @param {Event} ev
     */
    _onColorPickerSelect: function (ev) {
        if (ev.target === this.gradientColorPicker) {
            this._updateGradientColor(ev);
        } else {
            this._selectColor(Object.assign(this.getSelectedColors(), {
                color: ev.data.cssColor,
                target: this.colorPicker.el,
            }), 'custom_color_picked');
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSwitchPaneButtonClick(ev) {
        ev.stopPropagation();
        this._selectTabFromButton(ev.currentTarget);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientSliderClick(ev) {
        ev.stopPropagation();
        this._activateGradientSlider($(ev.target));
        this._updateGradient();
    },
    /**
     * Adds a color inside the gradient based on the position clicked within the preview.
     *
     * @private
     * @param {Event} ev
     */
    _onGradientPreviewClick(ev) {
        ev.stopPropagation();
        const offset = ev.offsetX;
        const width = parseInt(window.getComputedStyle(ev.target).width, 10);
        const position = 100 * offset / width;

        let previousColor;
        let nextColor;
        let previousPosition;
        let nextPosition;
        for (const slider of $(this.gradientEditorParts.sliders).find('input')) {
            if (slider.value < position) {
                previousColor = slider.dataset.color;
                previousPosition = slider.value;
            } else {
                nextColor = slider.dataset.color;
                nextPosition = slider.value;
                break;
            }
        }
        let color;
        if (previousColor && nextColor) {
            previousColor = ColorpickerWidget.convertCSSColorToRgba(previousColor);
            nextColor = ColorpickerWidget.convertCSSColorToRgba(nextColor);
            const previousRatio = (nextPosition - position) / (nextPosition - previousPosition);
            const nextRatio = 1 - previousRatio;
            const red = Math.round(previousRatio * previousColor.red + nextRatio * nextColor.red);
            const green = Math.round(previousRatio * previousColor.green + nextRatio * nextColor.green);
            const blue = Math.round(previousRatio * previousColor.blue + nextRatio * nextColor.blue);
            const opacity = Math.round(previousRatio * previousColor.opacity + nextRatio * nextColor.opacity);
            color = `rgba(${red}, ${green}, ${blue}, ${opacity / 100})`;
        } else {
            color = nextColor || previousColor || 'rgba(128, 128, 128, 0.5)';
        }

        const $slider = this._createGradientSlider(position, color);
        this._activateGradientSlider($slider);
        this._updateGradient();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onPanelClick(ev) {
        // Ignore to avoid closing popup.
        ev.stopPropagation();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientInputChange(ev) {
        this._updateGradient();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientInputKeyPress: function (ev) {
        if (ev.charCode === $.ui.keyCode.ENTER) {
            ev.preventDefault();
            this._onGradientInputChange();
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientButtonClick(ev) {
        const $buttons = $(ev.target).closest('span').find('we-button');
        $buttons.removeClass('active');
        $(ev.target).closest('we-button').addClass('active');
        this._updateGradient();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientButtonEnter(ev) {
        ev.stopPropagation();
        const $activeButton = $(ev.target).closest('span').find('we-button.active');
        const $buttons = $(ev.target).closest('span').find('we-button');
        $buttons.removeClass('active');
        $(ev.target).closest('we-button').addClass('active');
        this._updateGradient(true);
        $buttons.removeClass('active');
        $activeButton.addClass('active');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientButtonLeave(ev) {
        ev.stopPropagation();
        this.trigger_up('color_leave', Object.assign(this.getSelectedColors(), {
            target: ev.target,
        }));
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientCustomButtonClick(ev) {
        let gradient = this.gradientEditorParts.customButton.style['backgroundImage'];
        if (!gradient) {
            // default to first predefined
            gradient = this.pickers['predefined_gradients'].querySelector('button').dataset.color;
        }
        this._selectColor(Object.assign(this.getSelectedColors(), {
            color: gradient,
            target: this.gradientEditorParts.customButton,
        }), 'custom_color_picked');
        this._updateGradient();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientDeleteClick(ev) {
        ev.stopPropagation();
        const $activeSlider = $(this.pickers['custom_gradient'].querySelector('.o_slider_multi input.active'));
        $activeSlider.off();
        $activeSlider.remove();
        this.gradientEditorParts.deleteButton.classList.add('d-none');
        this.gradientEditorParts.deleteButton.classList.remove('active');
        this._updateGradient();
        this._activateGradientSlider($(this.pickers['custom_gradient'].querySelector('.o_slider_multi input')));
    },
});

//------------------------------------------------------------------------------
// Static
//------------------------------------------------------------------------------

/**
 * Load ColorPaletteWidget dependencies. This allows to load them without
 * instantiating the widget itself.
 *
 * @static
 */
let colorpickerTemplateProm;
ColorPaletteWidget.loadDependencies = async function (rpcCapableObj) {
    const proms = [ajax.loadXML('/web_editor/static/src/xml/snippets.xml', qweb)];

    // Public user using the editor may have a colorpalette but with
    // the default wysiwyg ones.
    if (!session.is_website_user) {
        // We can call the colorPalette multiple times but only need 1 rpc
        if (!colorpickerTemplateProm && !colorpickerArch) {
            colorpickerTemplateProm = rpcCapableObj._rpc({
                model: 'ir.ui.view',
                method: 'render_public_asset',
                args: ['web_editor.colorpicker', {}],
            }).then(arch => colorpickerArch = arch);
        }
        proms.push(colorpickerTemplateProm);
    }

    return Promise.all(proms);
};

return {
    ColorPaletteWidget: ColorPaletteWidget,
};
});
