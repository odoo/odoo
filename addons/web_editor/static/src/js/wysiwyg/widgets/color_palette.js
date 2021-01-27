odoo.define('web_editor.ColorPalette', function (require) {
'use strict';

const ajax = require('web.ajax');
const core = require('web.core');
const session = require('web.session');
const {ColorpickerWidget} = require('web.Colorpicker');
const Widget = require('web.Widget');
const summernoteCustomColors = require('web_editor.rte.summernote_custom_colors');
const weUtils = require('web_editor.utils');

const qweb = core.qweb;

const ColorPaletteWidget = Widget.extend({
    // ! for xmlDependencies, see loadDependencies function
    template: 'web_editor.snippet.option.colorpicker',
    events: {
        'click .o_we_color_btn': '_onColorButtonClick',
        'mouseenter .o_we_color_btn': '_onColorButtonEnter',
        'mouseleave .o_we_color_btn': '_onColorButtonLeave',
        'click .o_we_colorpicker_switch_pane_btn': '_onSwitchPaneButtonClick',
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
     * @param {JQuery} [options.$editable=$()] Editable content from which the custom colors are retrieved.
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.summernoteCustomColorsArray = [].concat(...summernoteCustomColors);
        this.style = window.getComputedStyle(document.documentElement);
        this.options = _.extend({
            selectedColor: false,
            resetButton: true,
            excluded: [],
            excludeSectionOf: null,
            $editable: $(),
            withCombinations: false,
        }, options || {});

        this.selectedColor = '';
        this.resetButton = this.options.resetButton;
        this.withCombinations = this.options.withCombinations;

        this.trigger_up('request_editable', {callback: val => this.options.$editable = val});
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

        const $colorSection = this.$('.o_colorpicker_sections[data-color-tab="theme-colors"]');
        const $clpicker = qweb.has_template('web_editor.colorpicker')
            ? $(qweb.render('web_editor.colorpicker'))
            : $(`<colorpicker><div class="o_colorpicker_section" data-name="common"></div></colorpicker>`);
        $clpicker.find('button').addClass('o_we_color_btn');
        $clpicker.appendTo($colorSection);

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
            const $commonColorSection = this.$('[data-name="common"]');
            summernoteCustomColors.forEach((colorRow, i) => {
                if (i === 0) {
                    return; // Ignore the summernote gray palette and use ours
                }
                const $div = $('<div/>', {class: 'clearfix'}).appendTo($commonColorSection);
                colorRow.forEach(color => {
                    $div.append(this._createColorButton(color, ['o_common_color']));
                });
            });
        }

        // Compute class colors
        const compatibilityColorNames = ['primary', 'secondary', 'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'success', 'info', 'warning', 'danger'];
        this.colorNames = [...compatibilityColorNames];
        this.colorToColorNames = {};
        this.el.querySelectorAll('button[data-color]').forEach(elem => {
            const colorName = elem.dataset.color;
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
        let defaultColor = this.selectedColor;
        if (defaultColor && !ColorpickerWidget.isCSSColor(defaultColor)) {
            defaultColor = weUtils.getCSSVariableValue(defaultColor, this.style);
        }
        this.colorPicker = new ColorpickerWidget(this, {
            defaultColor: defaultColor,
        });
        await this.colorPicker.prependTo($colorSection);

        // TODO Added as a fix. In master, the widget should probably not be
        // instantiated at all.
        if (this.options.excluded.includes('custom')) {
            this.colorPicker.$el.addClass('d-none');
        }

        return res;
    },
    /**
     * Return a list of the color names used in the color palette
     */
    getColorNames: function () {
        return this.colorNames;
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
        const existingColors = new Set(this.summernoteCustomColorsArray.concat(
            Object.keys(this.colorToColorNames)
        ));
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
        const $themeSection = this.$('.o_colorpicker_section[data-name="theme"]');
        const $button = this._createColorButton(color, classes);
        return $button.appendTo($themeSection);
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
        return {
            color: bgColor ? ColorpickerWidget.normalizeCSSColor(bgColor) : buttonEl.dataset.color || '',
            target: buttonEl,
        };
    },
    /**
     * Set the selectedColor and trigger an event
     *
     * @param {Object} color
     * @param {string} eventName
     */
    _selectColor: function (colorInfo, eventName) {
        this.selectedColor = colorInfo.color = this.colorToColorNames[colorInfo.color] || colorInfo.color;
        this.trigger_up(eventName, colorInfo);
        this._buildCustomColors();
        this._markSelectedColor();
    },
    /**
     * Mark the selected color
     *
     * @private
     */
    _markSelectedColor: function () {
        this.el.querySelectorAll('button.selected').forEach(el => el.classList.remove('selected'));
        const selectedButton = this.el.querySelector(`button[data-color="${this.selectedColor}"], button[style*="background-color:${this.selectedColor};"]`);
        if (selectedButton) {
            selectedButton.classList.add('selected');
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
        const colorInfo = this._getButtonInfo(buttonEl);
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
        this.trigger_up('color_hover', this._getButtonInfo(ev.currentTarget));
    },
    /**
     * Called when a color button is left the data color is the color currently selected.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonLeave: function (ev) {
        ev.stopPropagation();
        this.trigger_up('color_leave', {
            color: this.selectedColor,
            target: ev.target,
        });
    },
    /**
     * Called when an update is made on the colorpicker.
     *
     * @private
     * @param {Event} ev
     */
    _onColorPickerPreview: function (ev) {
        this.trigger_up('color_hover', {
            color: ev.data.cssColor,
            target: this.colorPicker.el,
        });
    },
    /**
     * Called when a color is selected on the colorpicker (mouseup).
     *
     * @private
     * @param {Event} ev
     */
    _onColorPickerSelect: function (ev) {
        this._selectColor({
            color: ev.data.cssColor,
            target: this.colorPicker.el,
        }, 'custom_color_picked');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSwitchPaneButtonClick(ev) {
        ev.stopPropagation();
        this.el.querySelectorAll('.o_we_colorpicker_switch_pane_btn').forEach(el => {
            el.classList.remove('active');
        });
        ev.currentTarget.classList.add('active');
        this.el.querySelectorAll('.o_colorpicker_sections').forEach(el => {
            el.classList.toggle('d-none', el.dataset.colorTab !== ev.currentTarget.dataset.target);
        });
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
    // the default summernote ones.
    if (!session.is_website_user) {
        // We can call the colorPalette multiple times but only need 1 rpc
        if (!colorpickerTemplateProm && !qweb.has_template('web_editor.colorpicker')) {
            colorpickerTemplateProm = rpcCapableObj._rpc({
                model: 'ir.ui.view',
                method: 'read_template',
                args: ['web_editor.colorpicker'],
            }).then(template => {
                return qweb.add_template('<templates>' + template + '</templates>');
            });
        }
        proms.push(colorpickerTemplateProm);
    }

    return Promise.all(proms);
};

return {
    ColorPaletteWidget: ColorPaletteWidget,
};
});
