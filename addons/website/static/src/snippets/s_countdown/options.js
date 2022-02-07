odoo.define('website.s_countdown_options', function (require) {
'use strict';

const core = require('web.core');
const options = require('web_editor.snippets.options');

const {ColorpickerWidget} = require('web.Colorpicker');
const weUtils = require('web_editor.utils');

const qweb = core.qweb;
const _t = core._t;

options.registry.countdown = options.Class.extend({
    xmlDependencies: ['/website/static/src/snippets/s_countdown/000.xml'],
    events: _.extend({}, options.Class.prototype.events || {}, {
        'click .toggle-edit-message': '_onToggleEndMessageClick',
    }),

    /**
     * @override
     */
    onBuilt() {
        this.layout(false, 'circle');
    },
    /**
     * Remove any preview classes, if present.
     *
     * @override
     */
    cleanForSave: async function () {
        this.$target.find('.s_countdown_canvas_wrapper').removeClass("s_countdown_none");
        this.$target.find('.s_countdown_end_message').removeClass("s_countdown_enable_preview");
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the countdown action at zero.
     *
     * @see this.selectClass for parameters
     */
    endAction: function (previewMode, widgetValue, params) {
        this.$target[0].dataset.endAction = widgetValue;
        if (widgetValue === 'message' || widgetValue === 'message_no_countdown') {
            if (!this.$target.find('.s_countdown_end_message').length) {
                const message = this.endMessage || qweb.render('website.s_countdown.end_message');
                this.$target.append(message);
            }
            this.$target.toggleClass('hide-countdown', widgetValue === 'message_no_countdown');
        } else {
            const $message = this.$target.find('.s_countdown_end_message').detach();
            if (this.showEndMessage) {
                this._onToggleEndMessageClick();
            }
            if ($message.length) {
                this.endMessage = $message[0].outerHTML;
            }
        }
    },
    /**
    * Changes the countdown style.
    *
    * @see this.selectClass for parameters
    */
    layout: function (previewMode, widgetValue, params) {
        this.$target[0].dataset.layout = widgetValue;
        this._render();

        if (widgetValue === 'circle') {
            this._update('progressBarStyle', 'surrounded');
            this._update('progressBarWeight', 'thin');
            this._update('layoutBackground', 'none');
        } else if (widgetValue === 'boxes') {
            this._update('progressBarStyle', 'none');
            this._update('layoutBackground', 'plain');
        }
    },
    /**
    * @override
    */
    selectDataAttribute: function (previewMode, widgetValue, params) {
        this._super(...arguments);
        this._update(params.attributeName);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    updateUIVisibility: async function () {
        await this._super(...arguments);
        const dataset = this.$target[0].dataset;

        // End Action UI
        this.$el.find('.toggle-edit-message')
            .toggleClass('d-none', dataset.endAction === 'nothing' || dataset.endAction === 'redirect');

        // End Message UI
        this.updateUIEndMessage();
    },
    /**
     * @see this.updateUI
     */
    updateUIEndMessage: function () {
        this.$target.find('.s_countdown_canvas_wrapper')
            .toggleClass("s_countdown_none", this.showEndMessage === true && this.$target.hasClass("hide-countdown"));
        this.$target.find('.s_countdown_end_message')
            .toggleClass("s_countdown_enable_preview", this.showEndMessage === true);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Ensures the color is an actual css color. In case of a color variable,
     * the color will be mapped to hexa.
     *
     * @private
     * @param {string} color
     * @returns {string}
     */
    _ensureCssColor: function (color) {
        if (ColorpickerWidget.isCSSColor(color)) {
            return color;
        }
        return weUtils.getCSSVariableValue(color) || this.defaultColor;
    },

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'endAction' || methodName === 'layout') {
            return this.$target[0].dataset[methodName];
        }
        return this._super(...arguments);
    },
    /**
     * Renders the countdown into the DOM.
     * @private
     */
    _render: function () {
        const $wrapper = this.$target.find('.s_countdown_canvas_wrapper');
        const svg = qweb.render(`website.s_countdown.graphics`, Object.assign({
            names: {'s': _t('Seconds'), 'm': _t('Minutes'), 'h': _('Hours'), 'd': _('Days')},
            sizes: {'s': 60, 'm': 60, 'h': 60, 'd': 15},
        }, this.$target[0].dataset));

        $wrapper.empty();
        $wrapper.append(svg);
    },
    /**
     * Updates the countdown to reflect changes to an attribute.
     *
     * @private
     * @param {string} attributeName - The attribute that was changed
     */
    _update: function (attributeName, value = undefined) {
        let offset = 0;

        value = value || this.$target[0].dataset[attributeName];
        this.$target[0].dataset[attributeName] = value;

        if (attributeName === 'display') {
            this._render();
        } else if (attributeName === 'progressBarWeight') {
            const stroke = value === 'thin' ? 3 : 10;
            offset = (this.$target[0].dataset.layoutBackground === 'inner' ? -1 : 1) * stroke / 2;
            this.$target[0].querySelectorAll('[stroke]:not(text)').forEach(el => {
                el.setAttribute('stroke-width', stroke);
            });
        } else if (attributeName === 'progressBarStyle') {
            this.$target.find('svg [opacity]').toggleClass('d-none', value !== 'surrounded');
            this.$target.find('svg [pathLength]').toggleClass('d-none', value === 'none');
            if (value === "none" && this.$target[0].dataset.layoutBackground === 'inner') {
                this.selectDataAttribute('layoutBackground', 'plain');
            }
        } else if (attributeName === 'layoutBackground') {
            const stroke = this.$target[0].dataset.progressBarWeight === 'thin' ? 3 : 10;
            offset = (value === 'inner' ? -1 : 1) * stroke / 2;
            this.$target.find('svg :not(text):not([stroke])').toggleClass('d-none', value === 'none');
        }

        if (offset) {
            this.$target[0].querySelectorAll('svg circle:first-child').forEach(el => {
                el.setAttribute('r', 45 + offset);
            });
            this.$target[0].querySelectorAll('svg rect:first-child').forEach(el => {
                el.setAttribute('x', 5 - offset);
                el.setAttribute('y', 5 - offset);
                el.setAttribute('width', 47 + 2 * offset);
                el.setAttribute('height', 90 + 2 * offset);
                el.setAttribute('rx', offset + 3.5);
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onToggleEndMessageClick: function () {
        this.showEndMessage = !this.showEndMessage;
        this.$el.find(".toggle-edit-message")
            .toggleClass('text-primary', this.showEndMessage);
        this.updateUIEndMessage();
        this.trigger_up('cover_update');
    },
});
});
