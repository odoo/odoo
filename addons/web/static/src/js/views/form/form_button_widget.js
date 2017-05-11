odoo.define('web.ButtonWidget', function (require) {
"use strict";

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
		this._super(parent);
		this.node = node;
		// the datapoint fetched from the model
        this.record = record;

        this.string = this.node.attrs.string;

	},
	start: function() {
		var self = this;
        this._super.apply(this, arguments);
        this.$el.click(function () {
            self.trigger_up('button_clicked', {
                attrs: self.node.attrs,
                record: self.record,
                show_wow: self.$el.hasClass('o_wow'),  // TODO: implement this (in view)
                callback: function() {
                    self.trigger_up('move_next');
                }
            });
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
            delay: { show: 1000, hide: 0 },
            trigger: 'focus',
            title: function() {
                return qweb.render('FocusTooltip', {
                    getFocusTip: self._getFocusTip(self.node)
                });
            }
        }, {});
        this.$el.tooltip(options);
    },
    _addTooltip: function(widget, $node) {
    	var self = this;
        this.$el.tooltip({
            delay: { show: 1000, hide: 0 },
            title: function () {
                return qweb.render('WidgetLabel.tooltip', {
                    debug: core.debug,
                    widget: self,
                });
            }
        });
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
    }
});

return ButtonWidget;

});
