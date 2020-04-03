odoo.define('web_editor.ColorPalette', function (require) {
'use strict';

const core = require('web.core');
const session = require('web.session');
const ColorpickerDialog = require('web.ColorpickerDialog');
const Dialog = require('web.Dialog');
const Widget = require('web.Widget');
const summernoteCustomColors = require('web_editor.rte.summernote_custom_colors');

const qweb = core.qweb;
const _t = core._t;

let templatePromise;

const ColorPaletteWidget = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/snippets.xml'],
    template: 'web_editor.snippet.option.colorpicker',
    events: {
        'click button': '_onColorButtonClick',
        'mouseenter button': '_onColorButtonEnter',
        'mouseleave button': '_onColorButtonLeave',
        'click .o_colorpicker_reset': '_onColorResetButtonClick',
        'click .o_add_custom_color': '_onCustomColorButtonClick',
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
        }, options || {});

        this.trigger_up('request_editable', {callback: val => this.options.$editable = val});
    },
    /**
     * @override
     */
    willStart: async function () {
        await this._super(...arguments);
        if (session.is_website_user) {
            // Public user using the editor may have a colorpalette but with
            // the default summernote ones.
            return;
        }
        // We can call the colorPalette multiple times but only need 1 rpc
        if (!templatePromise && !qweb.has_template('web_editor.colorpicker')) {
            templatePromise = this._rpc({
                model: 'ir.ui.view',
                method: 'read_template',
                args: ['web_editor.colorpicker'],
            }).then(template => {
                return qweb.add_template('<templates>' + template + '</templates>');
            });
        }
        await templatePromise;
    },
    /**
     * @override
     */
    start: function () {
        const res = this._super.apply(this, arguments);

        const $colorSection = this.$('.o_colorpicker_sections');
        const $wrapper = $colorSection.find('.o_colorpicker_section_tabs');
        const $clpicker = qweb.has_template('web_editor.colorpicker')
            ? $(qweb.render('web_editor.colorpicker'))
            : $(`<colorpicker><div class="o_colorpicker_section" data-name="common"></div></colorpicker>`);
        $clpicker.appendTo($wrapper);

        this.el.querySelectorAll('.o_colorpicker_section').forEach(elem => {
            $(elem).prepend('<div>' + (elem.dataset.display || '') + '</div>');
        });

        if (this.options.resetButton) {
            this.$('.o_colorpicker_reset').removeClass('d-none');
        }

        // Remove excluded palettes (note: only hide them to still be able
        // to remove their related colors on the DOM target)
        _.each(this.options.excluded, function (exc) {
            $colorSection.find('[data-name="' + exc + '"]').addClass('d-none');
        });
        if (this.options.excludeSectionOf) {
            $colorSection.find('[data-name]:has([data-color="' + this.options.excludeSectionOf + '"])').addClass('d-none');
        }

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

        // Render custom colors
        this._buildCustomColors();

        this._addCompatibilityColors(['primary', 'secondary', 'success', 'info', 'warning', 'danger']);

        // Compute class colors
        this.colorNames = [];
        this.colorToColorNames = {};
        this.el.querySelectorAll('button[data-color]').forEach(elem => {
            const colorName = elem.dataset.color;
            const $color = $(elem);
            $color.addClass('bg-' + colorName);
            this.colorNames.push(colorName);
            if (!elem.classList.contains('d-none')) {
                const color = ColorpickerDialog.normalizeCSSColor(this.style.getPropertyValue('--' + colorName).trim());
                this.colorToColorNames[color] = colorName;
            }
        });

        // Select selected Color
        if (this.options.selectedColor) {
            const selectedColor = ColorpickerDialog.normalizeCSSColor(this.options.selectedColor);
            this.selectedColor = this.colorToColorNames[selectedColor] || selectedColor;
            const selectedButton = this.el.querySelector(`button[data-color="${this.selectedColor}"], button[style*="background-color:${this.selectedColor};"]`);
            if (selectedButton) {
                selectedButton.classList.add('selected');
            }
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
     * Hardcode some existing colors (but make them hidden in the colorpicker)
     * so they can be removed from snippets when selecting another color.
     * Normally, the chosable colors do not contain them, which prevents them to
     * be removed. For example, normally, the 'alpha' and 'beta' color (which
     * are the same as primary and secondary) are displayed instead of their
     * duplicates... but not for all themes.
     *
     * @private
     * @param {string[]} colorNames
     */
    _addCompatibilityColors: function (colorNames) {
        for (const colorName of colorNames) {
            if (!this.$('button[data-color="' + colorName + '"]').length) {
                this.$el.append($('<button/>', {'class': 'd-none', 'data-color': colorName}));
            }
        }
    },
    /**
     * @private
     */
    _buildCustomColors: function () {
        if (this.options.excluded.includes('custom')) {
            return;
        }
        const existingColors = new Set(this.summernoteCustomColorsArray);
        this.trigger_up('get_custom_colors', {
            onSuccess: (colors) => {
                colors.forEach(color => {
                    this._addCustomColor(existingColors, color);
                });
            },
        });
        _.each(this.options.$editable.find('[style*="color"]'), el => {
            for (const colorProp of ['color', 'backgroundColor']) {
                this._addCustomColor(existingColors, el.style[colorProp]);
            }
        });
    },
    /**
     * Add the color to the custom color section if it is not in the existingColors.
     *
     * @param {string[]} existingColors Colors currently in the colorpicker
     * @param {string} color Color to add to the cuustom colors
     */
    _addCustomColor: function (existingColors, color) {
        const normColor = ColorpickerDialog.normalizeCSSColor(color);
        if (color && !existingColors.has(normColor)) {
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
        return this._createColorButton(color, classes).appendTo($themeSection);
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
            class: classes.join(' '),
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
        const color = bgColor ? ColorpickerDialog.normalizeCSSColor(bgColor) : buttonEl.dataset.color;
        return {
            color: color,
            target: buttonEl,
        };
    },
    /**
     * Set the selectedColor and inform parents
     *
     * @param {Object} colorInfo
     */
    _selectColor: function (colorInfo) {
        this.selectedColor = colorInfo.color = this.colorToColorNames[colorInfo.color] || colorInfo.color;
        this.trigger_up('color_picked', colorInfo);
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
        this._selectColor(colorInfo);
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
     * Called when a color button is left.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonLeave: function (ev) {
        ev.stopPropagation();
        const selected = this.el.querySelector('button.selected');
        let params = null;
        if (selected) {
            params = this._getButtonInfo(selected);
        } else {
            params = {
                color: '',
            };
        }
        params.target = ev.target;
        this.trigger_up('color_leave', params);
    },
    /**
     * Called when the color reset button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onColorResetButtonClick: function (ev) {
        this.selectedColor = false;
        this.trigger_up('color_reset', {
            target: ev.target,
        });
    },
    /**
     * Called when the custom color button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onCustomColorButtonClick: async function (ev) {
        const target = ev.target;
        let selectedColor = this.selectedColor;
        if (!ColorpickerDialog.isCSSColor(selectedColor)) {
            selectedColor = ColorpickerDialog.normalizeCSSColor(this.style.getPropertyValue('--' + selectedColor).trim());
        }
        const colorpicker = new ColorpickerDialog(this, {
            defaultColor: selectedColor,
        });
        colorpicker.on('colorpicker:saved', this, ev => {
            this._selectColor({
                color: ev.data.cssColor,
                target: target,
            });
        });
        colorpicker.open();
    },
});

const ColorPaletteDialog = Dialog.extend({
    /**
     * @override
     */
    init: function (parent, options) {
        this.options = options;
        this._super(parent, {
            size: 'small',
            title: _t('Pick a color'),
        });
    },
    /**
     * @override
     */
    start: function () {
        const proms = [this._super(...arguments)];
        const colorPalette = new ColorPaletteWidget(this, this.options);
        proms.push(colorPalette.appendTo(this.$el));
        return Promise.all(proms);
    },
});

return {
    ColorPaletteWidget: ColorPaletteWidget,
    ColorPaletteDialog: ColorPaletteDialog,
};
});
