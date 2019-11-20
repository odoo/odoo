odoo.define('web_editor.ColorPalette', function (require) {
'use strict';

const core = require('web.core');
const ColorPickerDialog = require('web.ColorpickerDialog');
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
     * @param {string[]} [options.targetClasses]
     * @param {string} [options.colorPrefix='bg-'] Used for the class based colors (theme).
     * @param {boolean} [options.resetButton=true] Whether to display or not the reset button.
     * @param {string[]} [options.excluded=[]] Sections not to display.
     * @param {string[]} [options.excludeSectionOf] Extra section to exclude: the one containing the named color.
     * @param {JQuery} [options.$editable=$()] Editable content from which the custom colors are retrieved.
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.summernoteCustomColorsArray = [].concat(...summernoteCustomColors).map((color) => this._convertHexToCssRgba(color));
        this.options = _.extend({
            selectedColor: false,
            targetClasses: [],
            colorPrefix: 'bg-',
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
        const res = this._super.apply(this, arguments);
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
        return res;
    },
    /**
     * @override
     */
    start: function () {
        const res = this._super.apply(this, arguments);

        const $wrapper = this.$('.o_colorpicker_section_tabs');
        $(qweb.render('web_editor.colorpicker')).appendTo($wrapper);

        this.el.querySelectorAll('.o_colorpicker_section').forEach(elem => {
            $(elem).prepend('<div>' + (elem.dataset.display || '') + '</div>');
        });

        if (this.options.resetButton) {
            this.$('.o_colorpicker_reset').removeClass('d-none');
        }

        // Remove excluded palettes
        _.each(this.options.excluded, function (exc) {
            $wrapper.find('[data-name="' + exc + '"]').remove();
        });
        if (this.options.excludeSectionOf) {
            $wrapper.find('[data-name]:has([data-color="' + this.options.excludeSectionOf + '"])').remove();
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
        this._buildCustomColor();

        // TODO refactor in master
        // The primary and secondary are hardcoded here (but marked as hidden)
        // so they can be removed from snippets when selecting another color.
        // Normally, the chosable colors do not contain them, which prevents
        // them to be removed. Indeed, normally, the 'alpha' and 'beta' colors
        // (which are the same) are displayed instead... but not for all themes.
        this.$el.append($('<button/>', {'class': 'd-none', 'data-color': 'primary'}));
        this.$el.append($('<button/>', {'class': 'd-none', 'data-color': 'secondary'}));

        // Compute class colors
        this.classes = [];
        this.el.querySelectorAll('button[data-color]').forEach(elem => {
            const color = elem.dataset.color;
            const $color = $(elem);
            $color.addClass('bg-' + color);
            const className = this.options.colorPrefix + color;
            if (this.options.targetClasses.includes(className)) {
                $color.addClass('selected');
            }
            this.classes.push(className);
        });

        return res;
    },
    /**
     * Return a list of the color classes used in the color palette
     */
    getClasses: function () {
        return this.classes;
    },
    /**
     * Reloads the color palette to get other custom colors on the page
     */
    reloadColorPalette: function () {
        this._buildCustomColor();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _buildCustomColor: function () {
        const existingColors = new Set(this.summernoteCustomColorsArray.concat(Array.from(this.el.querySelectorAll('.o_custom_color')).map(el => el.style.backgroundColor)));
        if (!this.options.excluded.includes('custom')) {
            Array.from(this.options.$editable.find('[style*="color"]')).forEach(el => {
                for (const colorProp of ['color', 'backgroundColor']) {
                    const color = el.style[colorProp];
                    if (color && !existingColors.has(color)) {
                        this._addCustomColorButton(color);
                        existingColors.add(color);
                    }
                }
            });
        }
    },
    /**
     * Add a custom button in the coresponding section.
     *
     * @private
     * @param {string} color Css rgb(a) string
     * @param {Array<string>} classes Classes added to the button
     */
    _addCustomColorButton: function (color, classes = []) {
        classes.push('o_custom_color');
        this._createColorButton(color, classes).appendTo(this.$('.o_colorpicker_section[data-name="theme"]'));
    },
    /**
     * Return a color button.
     *
     * @param {string} color Css rgb(a) string
     * @param {Array<string>} classes Classes added to the button
     */
    _createColorButton: function (color, classes) {
        const cssColor = this._convertHexToCssRgba(color);
        const selectedColor = this.options.selectedColor && this._convertHexToCssRgba(this.options.selectedColor);
        if (selectedColor === cssColor) {
            classes.push('selected');
        }
        return $('<button/>', {
            class: classes.join(' '),
            style: 'background-color:' + color + ';',
        });
    },
    /**
     * Return the hexadecimal css color as an rgb(a) css color: rgb((r, g, b) | rgba(r, g, b, a)
     *
     * @private
     * @param {string} hex Css hex string (#FFFFFF(FF))
     */
    _convertHexToCssRgba: function (hex) {
        if (!/^#([0-9A-F]{6}|[0-9A-F]{8})$/i.test(hex)) {
            return hex;
        }

        const red = parseInt(hex.substr(1, 2), 16);
        const blue = parseInt(hex.substr(3, 2), 16);
        const green = parseInt(hex.substr(5, 2), 16);
        if (hex.length === 9) {
            return _.str.sprintf('rgba(%s, %s, %s, %s)',
                red,
                blue,
                green,
                parseInt(hex.substr(7, 2), 16)
            );
        } else {
            return _.str.sprintf('rgb(%s, %s, %s)',
                red,
                blue,
                green
            );
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
        const target = ev.currentTarget;
        this.$('button.selected').removeClass('selected');
        $(target).addClass('selected');
        this.trigger_up('color_picked', {
            cssColor: target.style.backgroundColor || this.options.colorPrefix + target.dataset.color,
            isClass: !!target.dataset.color,
            target: ev.target,
        });
    },
    /**
     * Called when a color button is entered.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonEnter: function (ev) {
        ev.stopPropagation();
        const target = ev.currentTarget;
        this.trigger_up('color_hover', {
            cssColor: target.style.backgroundColor || this.options.colorPrefix + target.dataset.color,
            isClass: !!target.dataset.color,
            target: ev.target,
        });
    },
    /**
     * Called when a color button is left.
     *
     * @private
     * @param {Event} ev
     */
    _onColorButtonLeave: function (ev) {
        ev.stopPropagation();
        let params = {
            cssColor: '',
            isClass: false,
            target: ev.target,
        };
        const selected = this.el.querySelector('button.selected');
        if (selected) {
            params = {
                cssColor: selected.style.backgroundColor || this.options.colorPrefix + selected.dataset.color,
                isClass: !!selected.dataset.color,
                target: ev.target,
            };
        }
        this.trigger_up('color_leave', params);
    },
    /**
     * Called when the color reset button is clicked.
     *
     * @private
     * @param {Event} ev
     */
    _onColorResetButtonClick: function (ev) {
        this.$('button.selected').removeClass('selected');
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
        const originalEvent = ev;
        const $selected = this.$('button.selected');
        const colorpicker = new ColorPickerDialog(this, {
            defaultColor: this.options.defaultColor || $selected.css('background-color'),
        });
        colorpicker.on('colorpicker:saved', this, ev => {
            $selected.removeClass('selected');
            this._addCustomColorButton(ev.data.cssColor, ['selected']);
            this.trigger_up('custom_color_picked', {
                cssColor: ev.data.cssColor,
                target: originalEvent.target,
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
