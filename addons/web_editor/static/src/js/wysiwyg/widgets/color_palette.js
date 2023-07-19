/** @odoo-module **/

import { Colorpicker } from "@web/core/colorpicker/colorpicker";
import customColors from "@web_editor/js/editor/custom_colors";
import weUtils from "@web_editor/js/common/utils";
import {
    isCSSColor,
    normalizeCSSColor,
    convertCSSColorToRgba,
} from '@web/core/utils/colors';
import {
    Component,
    useRef,
    useState,
    onWillStart,
    onMounted,
    onWillUpdateProps,
} from "@odoo/owl";

export class ColorPalette extends Component {
    static template = 'web_editor.ColorPalette';
    static props = {
        document: { type: true, optional: true },
        resetTabCount: { type: Number, optional: true },
        selectedCC: { type: String, optional: true },
        selectedColor: { type: String, optional: true },
        resetButton: { type: Boolean, optional: true },
        excluded: { type: Array, optional: true },
        excludeSectionOf: { type: Array, optional: true },
        withCombinations: { type: Boolean, optional: true },
        noTransparency: { type: Boolean, optional: true },
        opacity: { type: Number, optional: true },
        selectedTab: { type: String, optional: true },
        withGradients: { type: Boolean, optional: true },
        getTemplate: { type: Function,  optional: true },
        onSetColorNames: { type: Function, optional: true },
        onColorHover: { type: Function, optional: true },
        onColorPicked: { type: Function, optional: true },
        onCustomColorPicked: { type: Function, optional: true },
        onColorLeave: { type: Function, optional: true },
        onInputEnter: { type: Function, optional: true },
        getCustomColors: { type: Function, optional: true },
        getEditableCustomColors: { type: Function, optional: true },
        onColorpaletteTabChange: { type: Function, optional: true },
    };
    static defaultProps = {
        document: window.document,
        resetTabCount: 0,
        resetButton: true,
        excluded: [],
        excludeSectionOf: null,
        withCombinations: false,
        noTransparency: false,
        opacity: 1,
        selectedTab: 'theme-colors',
        withGradients: false,
        onSetColorNames: () => {},
        onColorHover: () => {},
        onColorPicked: () => {},
        onCustomColorPicked: () => {},
        onColorLeave: () => {},
        onInputEnter: () => {},
        getCustomColors: () => [],
        getEditableCustomColors: () => [],
        onColorpaletteTabChange: () => {},
    }
    static components = { Colorpicker };
    elRef = useRef('el');
    state = useState({
        showGradientPicker: false,
    });
    setup() {
        this.init();
        onWillStart(async () => {
            if (this.props.getTemplate) {
                this.colorpickerTemplate = await this.props.getTemplate();
            }
        });
        onMounted(async () => {
            if (!this.elRef.el) {
                // There is legacy code that can trigger the instantiation of the
                // link tool when one of it's parent component is not in the dom. If
                // that parent element is not in the dom, owl will not return
                // `this.linkComponentWrapperRef.el` because of a check (see
                // `inOwnerDocument`).
                // Todo: this workaround should be removed when the snippet menu is
                // converted to owl.
                await new Promise(resolve => {
                    const observer = new MutationObserver(() => {
                        if (this.elRef.el) {
                            observer.disconnect();
                            resolve();
                        }
                    });
                    observer.observe(document.body, { childList: true, subtree: true });
                });
            }
            this.el = this.elRef.el;
            const $el = $(this.el);
            this.$ = $el.find.bind($el);

            $el.on('click', '.o_we_color_btn', this._onColorButtonClick.bind(this));
            $el.on('mouseenter', '.o_we_color_btn', this._onColorButtonEnter.bind(this));
            $el.on('mouseleave', '.o_we_color_btn', this._onColorButtonLeave.bind(this));

            $el.on('click', '.o_custom_gradient_editor .o_custom_gradient_btn', this._onGradientCustomButtonClick.bind(this));
            $el.on('click', '.o_custom_gradient_editor', this._onPanelClick.bind(this));
            $el.on('change', '.o_custom_gradient_editor input[type="text"]', this._onGradientInputChange.bind(this));
            $el.on('keypress', '.o_custom_gradient_editor input[type="text"]', this._onGradientInputKeyPress.bind(this));
            $el.on('click', '.o_custom_gradient_editor we-button:not(.o_remove_color)', this._onGradientButtonClick.bind(this));
            $el.on('mouseenter', '.o_custom_gradient_editor we-button:not(.o_remove_color)', this._onGradientButtonEnter.bind(this));
            $el.on('mouseleave', '.o_custom_gradient_editor we-button:not(.o_remove_color)', this._onGradientButtonLeave.bind(this));

            $el.on('click', '.o_custom_gradient_scale', this._onGradientPreviewClick.bind(this));
            // Note: _onGradientSliderClick on slider is attached at slider creation.
            $el.on('click', '.o_custom_gradient_editor .o_remove_color', this._onGradientDeleteClick.bind(this));

            await this.start();
        });
        onWillUpdateProps((newProps) => {
            this._updateColorToColornames();
            if (this.props.resetTabCount !== newProps.resetTabCount) {
                this._selectDefaultTab();
            }
            if (this.props.selectedCC !== newProps.selectedCC || this.props.selectedColor !== newProps.selectedColor) {
                this._selectColor({
                    ccValue: newProps.selectedCC,
                    color: newProps.selectedColor,
                });
            }
            this._buildCustomColors();
            this._markSelectedColor();
        });
    }
    init() {
        const editableDocument = this.props.document;
        this.style = editableDocument.defaultView.getComputedStyle(editableDocument.documentElement);
        this.selectedColor = '';
        this.resetButton = this.props.resetButton;
        this.withCombinations = this.props.withCombinations;
        this.selectedTab = this.props.selectedTab;

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
            pickers: this.props.withGradients ? [
                'predefined_gradients',
                'custom_gradient',
            ] : [],
        }];

        this.sections = {};
        this.pickers = {};
    }
    /**
     * @override
     */
    async start() {
        const switchPaneButtons = this.el.querySelectorAll('.o_we_colorpicker_switch_pane_btn');

        let colorpickerEl;
        if (this.colorpickerTemplate) {
            colorpickerEl = $(this.colorpickerTemplate)[0];
        } else {
            colorpickerEl = document.createElement("colorpicker");
            const sectionEl = document.createElement('DIV');
            sectionEl.classList.add('o_colorpicker_section');
            sectionEl.dataset.name = 'common';
            colorpickerEl.appendChild(sectionEl);
        }
        colorpickerEl.querySelectorAll('button').forEach(el => el.classList.add('o_we_color_btn'));

        // Populate tabs based on the tabs configuration indicated in this.tabs
        this.tabs.forEach((tab, index) => {
            // Append pickers to section
            let sectionEl = this.el.querySelector(`.o_colorpicker_sections[data-color-tab="${tab.id}"]`);
            const container = sectionEl.querySelector('.o_colorpicker_section_container');
            if (container) {
                sectionEl = container;
            }
            let sectionIsEmpty = true;
            tab.pickers.forEach((pickerId) => {
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

                    if (!this.props.excluded.includes(pickerId)) {
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
                if (this.selectedTab === tab.id) {
                    this.selectedTab = this.tabs[(index + 1) % this.tabs.length].id;
                }
            }
            this.sections[tab.id] = sectionEl;
        });

        // Predefined gradient opacity
        if (this.props.withGradients && this.props.opacity !== 1) {
            this.pickers['predefined_gradients'].querySelectorAll('button').forEach(elem => {
                let gradient = elem.dataset.color;
                gradient = gradient.replaceAll(/rgba?(\(\s*\d+\s*,\s*\d+\s*,\s*\d+)(?:\s*,.+?)?\)/g,
                    `rgba$1, ${this.props.opacity})`);
                elem.dataset.color = gradient.replaceAll(/\s+/g, '');
            });
        }

        // Palette for gradient
        if (this.pickers['custom_gradient']) {
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
            const gradient = weUtils.isColorGradient(this.props.selectedColor) && this.props.selectedColor;
            this._selectGradient(gradient);
            const resizeObserver = new window.ResizeObserver(() => {
                this._adjustActiveSliderDelete();
            });
            resizeObserver.observe(this.gradientEditorParts.sliders);
        }

        // Switch to the correct tab
        const selectedButtonIndex = this.tabs.map(tab => tab.id).indexOf(this.selectedTab);
        this._selectTabFromButton(this.el.querySelectorAll('button')[selectedButtonIndex]);

        // Remove the buttons display if there is only one
        const visibleButtons = Array.from(switchPaneButtons).filter(button => !button.classList.contains('d-none'));
        if (visibleButtons.length === 1) {
            visibleButtons[0].classList.add('d-none');
        }

        // Remove excluded palettes (note: only hide them to still be able
        // to remove their related colors on the DOM target)
        this.props.excluded.forEach((exc) => {
            this.$('[data-name="' + exc + '"]').addClass('d-none');
        });
        if (this.props.excludeSectionOf) {
            this.$('[data-name]:has([data-color="' + this.props.excludeSectionOf + '"])').addClass('d-none');
        }

        this.el.querySelectorAll('.o_colorpicker_section').forEach(elem => {
            $(elem).prepend('<div>' + (elem.dataset.display || '') + '</div>');
        });

        // Render common colors
        if (!this.props.excluded.includes('common')) {
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

        this.colorNames = [...weUtils.COLOR_PALETTE_COMPATIBILITY_COLOR_NAMES];
        this._updateColorToColornames();
        this.props.onSetColorNames([...this.colorNames]);

        // Select selected Color and build customColors.
        // If no color is selected selectedColor is an empty string (transparent is interpreted as no color)
        if (this.props.selectedCC) {
            this.selectedCC = this.props.selectedCC;
        }
        this._setSelectedColor(this.props.selectedColor);
        this._buildCustomColors();
        this._markSelectedColor();

        // Colorpicker
        if (!this.props.excluded.includes('custom')) {
            let defaultColor = this.selectedColor;
            if (defaultColor && !isCSSColor(defaultColor)) {
                defaultColor = weUtils.getCSSVariableValue(defaultColor, this.style);
            }
            if (!defaultColor && this.props.opacity !== 1) {
                defaultColor = 'rgba(0, 0, 0, ' + this.props.opacity + ')';
            }
            this.state.customDefaultColor = defaultColor;
        }
    }
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Gets the currently selected colors.
     *
     * @private
     * @returns {Object} ccValue and color (plain color or gradient).
     */
    _getSelectedColors() {
        return {
            ccValue: this.selectedCC,
            color: this.selectedColor,
        };
    }
    /**
     * @private
     */
    _setSelectedColor(color) {
        if (color) {
            if (color === 'rgba(0, 0, 0, 0)' && this.props.opacity !== 1) {
                color = 'rgba(0, 0, 0, ' + this.props.opacity + ')';
            }
            let selectedColor = color;
            if (weUtils.COLOR_PALETTE_COMPATIBILITY_COLOR_NAMES.includes(selectedColor)) {
                selectedColor = weUtils.getCSSVariableValue(selectedColor, this.style) || selectedColor;
            }
            selectedColor = normalizeCSSColor(selectedColor);
            if (selectedColor !== 'rgba(0, 0, 0, 0)') {
                this.selectedColor = this.colorToColorNames[selectedColor] || selectedColor;
            }
        }
    }
    /**
     * @private
     */
    _buildCustomColors() {
        if (this.props.excluded.includes('custom')) {
            return;
        }
        this.el.querySelectorAll('.o_custom_color').forEach(el => el.remove());
        const existingColors = new Set(Object.keys(this.colorToColorNames));
        for (const color of this.props.getCustomColors()) {
            this._addCustomColor(existingColors, color);
        }
        weUtils.getCSSVariableValue('custom-colors', this.style).split(' ').forEach(v => {
            const color = weUtils.getCSSVariableValue(v.substring(1, v.length - 1), this.style);
            if (isCSSColor(color)) {
                this._addCustomColor(existingColors, color);
            }
        });
        for (const color of this.props.getEditableCustomColors()) {
            this._addCustomColor(existingColors, color);
        }
        if (this.selectedColor) {
            this._addCustomColor(existingColors, this.selectedColor);
        }
    }
    /**
     * Add the color to the custom color section if it is not in the existingColors.
     *
     * @param {string[]} existingColors Colors currently in the colorpicker
     * @param {string} color Color to add to the cuustom colors
     */
    _addCustomColor(existingColors, color) {
        if (!color) {
            return;
        }
        if (!isCSSColor(color)) {
            color = weUtils.getCSSVariableValue(color, this.style);
        }
        const normColor = normalizeCSSColor(color);
        if (!existingColors.has(normColor)) {
            this._addCustomColorButton(normColor);
            existingColors.add(normColor);
        }
    }
    /**
     * Add a custom button in the coresponding section.
     *
     * @private
     * @param {string} color
     * @param {string[]} classes - classes added to the button
     * @returns {jQuery}
     */
    _addCustomColorButton(color, classes = []) {
        classes.push('o_custom_color');
        const $button = this._createColorButton(color, classes);
        return $button.appendTo(this.pickers['custom']);
    }
    /**
     * Return a color button.
     *
     * @param {string} color
     * @param {string[]} classes - classes added to the button
     * @returns {jQuery}
     */
    _createColorButton(color, classes) {
        return $('<button/>', {
            class: 'o_we_color_btn ' + classes.join(' '),
            style: 'background-color:' + color + ';',
        });
    }
    /**
     * Gets normalized information about a color button.
     *
     * @private
     * @param {HTMLElement} buttonEl
     * @returns {Object}
     */
    _getButtonInfo(buttonEl) {
        const bgColor = buttonEl.style.backgroundColor;
        const value = buttonEl.dataset.color || (bgColor && bgColor !== 'initial' ? normalizeCSSColor(bgColor) : '') || '';
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
    }
    /**
     * Set the selectedColor and trigger an event
     *
     * @param {Object} colorInfo
     * @param {string} [colorInfo.ccValue]
     * @param {string} [colorInfo.color]
     * @param {Function} [eventCallback]
     */
    _selectColor(colorInfo, eventCallback) {
        this.selectedCC = colorInfo.ccValue;
        this.selectedColor = colorInfo.color = this.colorToColorNames[colorInfo.color] || colorInfo.color;
        if (eventCallback) {
            eventCallback(colorInfo);
        }
        this._buildCustomColors();
        this.state.customSelectedColor = colorInfo.color;
        const customGradient = weUtils.isColorGradient(colorInfo.color) ? colorInfo.color : false;
        if (this.pickers['custom_gradient']) {
            this._selectGradient(customGradient);
        }
        this._markSelectedColor();
    }
    /**
     * Populates the gradient editor.
     *
     * @private
     * @param {string} gradient CSS string
     */
    _selectGradient(gradient) {
        const editor = this.gradientEditorParts;
        this.state.showGradientPicker = false;
        const colorSplits = [];
        if (gradient) {
            const colorTesterEl = document.createElement("div");
            colorTesterEl.style.display = "none";
            document.body.appendChild(colorTesterEl);
            const colorTesterStyle = window.getComputedStyle(colorTesterEl);
            gradient = gradient.toLowerCase();
            // Extract colors and their positions: colors can either be in the #rrggbb format,
            // in the rgb/rgba(...) format or as color name, positions are expected to be
            // expressed as percentages (lengths are not supported).
            for (const entry of gradient.matchAll(/(#[0-9a-f]{6}|rgba?\(\s*[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+\s*[,\s*[0-9.]*]?\s*\)|[a-z]+)\s*([[0-9]+%]?)/g)) {
                colorTesterEl.style.color = entry[1];
                // Ignore unknown color.
                if (!colorTesterEl.style.color) {
                    continue;
                }
                const color = colorTesterStyle.color;
                colorSplits.push([color, entry[2].replace('%', '')]);
            }
            colorTesterEl.remove();
        }
        // Consider unsupported gradients as not gradients.
        if (!gradient || colorSplits.length < 2) {
            $(editor.customContent).addClass('d-none');
            editor.customButton.style['background-image'] = '';
            delete editor.customButton.dataset.color;
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
    }
    /**
     * Adjusts the visibility of the gradient editor elements.
     *
     * @private
     * @param {boolean} isLinear
     */
    _updateGradientVisibility(isLinear) {
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
    }
    /**
     * Removes the transparency from an rgba color.
     *
     * @private
     * @param {string} color rgba CSS color string
     * @returns {string} rgb CSS color string
     */
    _opacifyColor(color) {
        if (color.startsWith('rgba')) {
            return color.replace('rgba', 'rgb').replace(/,\s*[0-9.]+\s*\)/, ')');
        }
        return color;
    }
    /**
     * Creates and adds a slider for the gradient color definition.
     *
     * @private
     * @param {int} position between 0 and 100
     * @param {string} color
     * @returns {jQuery} created slider
     */
    _createGradientSlider(position, color) {
        const $slider = $('<input class="w-100" type="range" min="0" max="100"/>');
        $slider.attr('value', position);
        $slider.attr('data-color', color);
        $slider.css('color', this._opacifyColor(color));
        $slider.on('click', this._onGradientSliderClick.bind(this));
        $slider.appendTo(this.gradientEditorParts.sliders);
        this._sortGradientSliders();
        return $slider;
    }
    /**
     * Activates a slider of the gradient color definition.
     *
     * @private
     * @param {jQuery} $slider
     */
    _activateGradientSlider($slider) {
        const $sliders = $(this.gradientEditorParts.sliders).find('input');
        $sliders.removeClass('active');
        $slider.addClass('active');

        const color = $slider.data('color');
        this.state.showGradientPicker = true;
        this.state.gradientSelectedColor = color;
        this._sortGradientSliders();
        this._adjustActiveSliderDelete();
    }
    /**
     * Adjusts the position of the slider delete button.
     *
     * @private
     */
    _adjustActiveSliderDelete() {
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
    }
    /**
     * Reorders the sliders of the gradient color definition by their position.
     *
     * @private
     */
    _sortGradientSliders() {
        const $sliderInputs = $(this.gradientEditorParts.sliders).find('input');
        for (const slider of $sliderInputs.sort((a, b) => parseInt(a.value, 10) - parseInt(b.value, 10))) {
            this.gradientEditorParts.sliders.appendChild(slider);
        }
    }
    /**
     * Computes the customized gradient from the custom gradient editor.
     *
     * @private
     * @returns {string} gradient string corresponding to the currently selected options.
     */
    _computeGradient() {
        const editor = this.gradientEditorParts;

        const $picker = $(this.pickers['custom_gradient']);

        const colors = [];
        for (const slider of $(editor.sliders).find('input')) {
            const color = convertCSSColorToRgba($(slider).data('color'));
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
    }
    /**
     * Computes the customized gradient from the custom gradient editor and displays it.
     *
     * @private
     * @param {boolean} isPreview
     */
    _updateGradient(isPreview) {
        const gradient = this._computeGradient();
        // Avoid updating an unchanged gradient.
        if (weUtils.areCssValuesEqual(gradient, this.selectedColor) && !isPreview) {
            return;
        }
        const params = {
            ...this._getSelectedColors(),
            color: gradient,
        };
        if (isPreview) {
            this.props.onColorHover(params);
        } else {
            this.props.onColorPicked(params);
        }
    }
    /**
     * Marks the selected colors.
     *
     * @private
     */
    _markSelectedColor() {
        for (const buttonEl of this.el.querySelectorAll('button')) {
            // TODO buttons should only be search by data-color value
            // instead of style but seems necessary for custom colors right
            // now...
            const value = buttonEl.dataset.color || buttonEl.style.backgroundColor;
            // Buttons in the theme-colors tab of the palette have
            // no opacity, hence they should be searched by removing
            // opacity of 0.6 (which was applied by default) from
            // the selected color.
            const isCommonColor = buttonEl.classList.contains('o_common_color');
            const selectedColor = isCommonColor ? this._opacifyColor(this.selectedColor) : this.selectedColor;
            buttonEl.classList.toggle('selected', value
                && (this.selectedCC === value || weUtils.areCssValuesEqual(selectedColor, value)));
        }
    }

    /**
     * Select the default tab.
     *
     * @private
     */
    _selectDefaultTab() {
        const selectedButtonIndex = this.tabs.map(tab => tab.id).indexOf(this.selectedTab);
        this._selectTabFromButton(this.el.querySelectorAll('button')[selectedButtonIndex]);
    }
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
        this.props.onColorpaletteTabChange(buttonEl.dataset.target);
    }
    /**
     * Updates a gradient color from a selection in the color picker.
     *
     * @private
     * @param {String} colorInfo.cssColor
     * @param {Boolean} isPreview
     */
    _updateGradientColor(colorInfo, isPreview) {
        const $slider = $(this.gradientEditorParts.sliders).find('input.active');
        if (!weUtils.areCssValuesEqual(colorInfo.cssColor, $slider.data('color'))) {
            const previousColor = $slider.data('color');
            $slider.data('color', colorInfo.cssColor);
            this._updateGradient(isPreview);
            if (isPreview) {
                $slider.data('color', previousColor);
            }
        }
    }
    /**
     * @private
     */
    _updateColorToColornames() {
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
            } else if (weUtils.EDITOR_COLOR_CSS_VARIABLES.includes(colorName)) {
                elem.style.backgroundColor = `var(--we-cp-${colorName})`;
            } else {
                elem.classList.add(`bg-${colorName}`);
            }
            this.colorNames.push(colorName);
            if (!isCCName && !elem.classList.contains('d-none')) {
                const color = weUtils.getCSSVariableValue(colorName, this.style);
                this.colorToColorNames[color] = colorName;
            }
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a color button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonClick(ev) {
        const buttonEl = ev.currentTarget;
        const colorInfo = {
            ...this._getSelectedColors(),
            ...this._getButtonInfo(buttonEl)
        };
        this._selectColor(colorInfo, this.props.onColorPicked);
    }
    /**
     * Called when a color button is entered.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonEnter(ev) {
        this.props.onColorHover({
            ...this._getSelectedColors(),
            ...this._getButtonInfo(ev.currentTarget)
        });
    }
    /**
     * Called when a color button is left the data color is the color currently selected.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonLeave(ev) {
        this.props.onColorLeave({
            ...this._getSelectedColors(),
            target: ev.target,
        });
    }
    /**
     * Called when an update is made on the colorpicker.
     *
     * @private
     * @param {Object} colorInfo
     */
    _onColorPickerPreview(colorInfo) {
        this.props.onColorHover({
            ...this._getSelectedColors(),
            color: colorInfo.cssColor,
        });
    }
    /**
     * Called when an update is made on the gradient colorpicker.
     *
     * @private
     * @param {Object} colorInfo
     */
    _onColorPickerPreviewGradient(colorInfo) {
        this._updateGradientColor(colorInfo, true);
    }
    /**
     * Called when a color is selected on the colorpicker (mouseup).
     *
     * @private
     * @param {Object} colorInfo
     */
    _onColorPickerSelect(colorInfo) {
        this._selectColor({
            ...this._getSelectedColors(),
            color: colorInfo.cssColor,
        }, this.props.onCustomColorPicked);
    }
    /**
     * Called when a color is selected on the gradient colorpicker (mouseup).
     *
     * @private
     * @param {Object} colorInfo
     */
    _onColorPickerSelectGradient(colorInfo) {
        this._updateGradientColor(colorInfo);
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onSwitchPaneButtonClick(ev) {
        ev.stopPropagation();
        this._selectTabFromButton(ev.currentTarget);
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientSliderClick(ev) {
        ev.stopPropagation();
        this._activateGradientSlider($(ev.target));
        this._updateGradient();
    }
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
            previousColor = convertCSSColorToRgba(previousColor);
            nextColor = convertCSSColorToRgba(nextColor);
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
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onPanelClick(ev) {
        // Ignore to avoid closing popup.
        ev.stopPropagation();
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientInputChange(ev) {
        this._updateGradient();
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientInputKeyPress(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._onGradientInputChange();
        }
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientButtonClick(ev) {
        const $buttons = $(ev.target).closest('span').find('we-button');
        $buttons.removeClass('active');
        $(ev.target).closest('we-button').addClass('active');
        this._updateGradient();
    }
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
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onGradientButtonLeave(ev) {
        ev.stopPropagation();
        this.props.onColorLeave({
            ...this._getSelectedColors(),
            target: ev.target,
        });
    }
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
        this._selectColor({
            ...this._getSelectedColors(),
            color: gradient,
            target: this.gradientEditorParts.customButton,
        }, this.props.onCustomColorPicked);
        this._updateGradient();
    }
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
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onColorpickerClick(ev) {
        if (ev.target.matches(".o_colorpicker_section, .o_colorpicker_sections")) {
            ev.stopPropagation();
        }
    }
}
