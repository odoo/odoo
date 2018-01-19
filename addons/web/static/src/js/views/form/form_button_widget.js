odoo.define('web.ButtonWidget', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var ViewWidget = require('web.ViewWidget');

var _t = core._t;
var qweb = core.qweb;

var ButtonWidget = ViewWidget.extend({
    template: 'WidgetButton',
    /**
     * Button Widget  class
     *
     * @constructor
     * @param {Widget} parent
     * @param {string} node
     * @param {Object} record A record object (result of the get method of a basic model)
     * @param {Object} [options]
     * @param {string} [options.mode=readonly] should be 'readonly' or 'edit'
     */
    init: function (parent, node, record, options) {
        this._super(parent, record);

        this.node = node;
        this.__node = node; // TODO: get rid of this, added because we are finding first button based on this

        // the 'string' property is a human readable (and translated) description of the button.
        this.string = (this.node.attrs.string || '').replace(/_/g, '');

        if (node.attrs.icon) {
            this.fa_icon = node.attrs.icon.indexOf('fa-') === 0;
        }
    },
    start: function () {
        var self = this;
        this._super.apply(this, arguments);
        var enterPressed = false;
        this.$el.click(function () {
            if (enterPressed) {
                self.trigger_up('set_last_tabindex', {target: self});
            }
            self.trigger_up('button_clicked', {
                attrs: self.node.attrs,
                record: self.record,
                callback: function (direction) {
                    self.trigger_up('navigation_move', {direction: direction || 'next'});
                }
            });
        });

        // Display tooltip
        if (config.debug || this.node.attrs.help) {
            this._addButtonTooltip();
        }

        this.$el.on('keydown', function (e) {
            // Note: For setting enterPressed variable which will be helpful to set next widget or not,
            // if mouse is used then do not set next widget focus
            e.stopPropagation();
            if (e.which === $.ui.keyCode.ENTER) {
                enterPressed = true;
            }
        });
        this._addOnFocusAction();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {jQuery} the focusable element
     */
    getFocusableElement: function () {
        return this.$el || $();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a tooltip on a button
     *
     * @private
     * @param {Object} node
     * @param {jQuery} $button
     */
    _addButtonTooltip: function () {
        var self = this;
        this.$el.tooltip({
            delay: { show: 1000, hide: 0 },
            title: function () {
                return qweb.render('WidgetButton.tooltip', {
                    debug: config.debug,
                    state: self.record,
                    node: self.node,
                });
            },
        });
    },
    /**
     * When focus comes to button show tip on it,
     * this function will display tip to explain user what this button will do,
     * this function will _getFocusTip function to get tip on the button,
     * tip is either explicitly defined as an on_focus_tip attribute else _getFocusTip will return current button string.
     * @private
     */
    _addOnFocusAction: function () {
        var self = this;
        var options = _.extend({
            delay: {show: 1000, hide: 0},
            trigger: 'focus',
            title: function () {
                return qweb.render('FocusTooltip', {
                    getFocusTip: self._getFocusTip(self.node)
                });
            }
        }, {});
        this.$el.tooltip(options);
    },
    /**
     * Return on_focus_tip attribute if available else will return current button string
     *
     * @private
     * @param {Object} node
     */
    _getFocusTip: function (node) {
        var showFocusTip = function () {
            return node.attrs.on_focus_tip ? node.attrs.on_focus_tip : _.str.sprintf(_t('Press ENTER to %s'), node.attrs.string);
        };
        return showFocusTip;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * _onKeydown on ViewWidget will move user to next widget as soon as Enter key is pressed
     * Next button/widget should be focused once reload is done and once lastTabindex variable is set
     * So here we skip Enter key, click handler will do the job of trigerring navigation_move once button operation is complete
     *
     * @override
     * @private
     * @param {KeyEvent} ev
     */
    _onKeydown: function (ev) {
        if (ev.which === $.ui.keyCode.ENTER) {
            return;
        }
        return this._super.apply(this, arguments);
    },
});

return ButtonWidget;

});
