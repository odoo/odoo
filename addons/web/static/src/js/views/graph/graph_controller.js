odoo.define('web.GraphController', function (require) {
"use strict";
/*---------------------------------------------------------
 * Odoo Graph view
 *---------------------------------------------------------*/

var AbstractController = require('web.AbstractController');
var core = require('web.core');

var qweb = core.qweb;

var GraphController = AbstractController.extend({
    className: 'o_graph',
    /**
     * @override
     * @param {Widget} parent
     * @param {GraphModel} model
     * @param {GraphRenderer} renderer
     * @param {Object} params
     * @param {string[]} params.measures
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.measures = params.measures;
    },
    /**
     * @todo check if this can be removed (mostly duplicate with
     * AbstractController method)
     */
    destroy: function () {
        if (this.$buttons) {
            // remove jquery's tooltip() handlers
            this.$buttons.find('button').off().tooltip('destroy');
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Render the buttons according to the GraphView.buttons and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     *
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should
     * be inserted $node may be undefined, in which case the GraphView does
     * nothing
     */
    renderButtons: function ($node) {
        if ($node) {
            var context = {measures: _.pairs(_.omit(this.measures, '__count__'))};
            this.$buttons = $(qweb.render('GraphView.buttons', context));
            this.$measureList = this.$buttons.find('.o_graph_measures_list');
            this.$buttons.find('button').tooltip();
            this.$buttons.click(this._onButtonClick.bind(this));
            this._updateButtons();
            this.$buttons.appendTo($node);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @todo remove this and directly calls update. Update should be overridden
     * and modified to call _updateButtons
     *
     * @param {string} mode one of 'pie', 'line' or 'bar'
     */
    _setMode: function (mode) {
        this.update({mode: mode});
        this._updateButtons();
    },
    /**
     * @todo same as _setMode
     *
     * @param {string} measure should be a valid (and aggregatable) field name
     */
    _setMeasure: function (measure) {
        var self = this;
        this.update({measure: measure}).then(function () {
            self._updateButtons();
        });
    },
    /**
     * makes sure that the buttons in the control panel matches the current
     * state (so, correct active buttons and stuff like that)
     */
    _updateButtons: function () {
        var state = this.model.get();
        this.$buttons.find('.o_graph_button').removeClass('active');
        this.$buttons
            .find('.o_graph_button[data-mode="' + state.mode + '"]')
            .addClass('active');
        this.$measureList.find('li').each(function (index, li) {
            $(li).toggleClass('selected', $(li).data('field') === state.measure);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Do what need to be done when a button from the control panel is clicked.
     *
     * @param {MouseEvent} event
     */
    _onButtonClick: function (event) {
        var $target = $(event.target);
        if ($target.hasClass('o_graph_button')) {
            this._setMode($target.data('mode'));
        } else if ($target.parents('.o_graph_measures_list').length) {
            event.preventDefault();
            event.stopPropagation();
            var parent = $target.parent();
            var field = parent.data('field');
            this._setMeasure(field);
        }
    },
});

return GraphController;

});
