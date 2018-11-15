odoo.define('web.GraphController', function (require) {
"use strict";
/*---------------------------------------------------------
 * Odoo Graph view
 *---------------------------------------------------------*/

var core = require('web.core');
var AbstractController = require('web.AbstractController');
var GroupByMenuInterfaceMixin = require('web.GroupByMenuInterfaceMixin');

var qweb = core.qweb;

var GraphController = AbstractController.extend(GroupByMenuInterfaceMixin,{
    className: 'o_graph',

    /**
     * @override
     * @param {Widget} parent
     * @param {GraphModel} model
     * @param {GraphRenderer} renderer
     * @param {Object} params
     * @param {string[]} params.measures
     * @param {boolean} params.isEmbedded
     * @param {string[]} params.groupableFields,
     */
    init: function (parent, model, renderer, params) {
        GroupByMenuInterfaceMixin.init.call(this);
        this._super.apply(this, arguments);
        this.measures = params.measures;
        // this parameter condition the appearance of a 'Group By'
        // button in the control panel owned by the graph view.
        this.isEmbedded = params.isEmbedded;
        // this parameter determines what is the list of fields
        // that may be used within the groupby menu available when
        // the view is embedded
        this.groupableFields = params.groupableFields;
        // extends custom_events key. This allow the controller
        // to listen to information comming from the groupby menu.
        // this is used when the view is embedded.
    },
    /**
     * @todo check if this can be removed (mostly duplicate with
     * AbstractController method)
     */
    destroy: function () {
        if (this.$buttons) {
            // remove jquery's tooltip() handlers
            this.$buttons.find('button').off().tooltip('dispose');
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the current mode, measure and groupbys, so we can restore the
     * view when we save the current state in the search view, or when we add it
     * to the dashboard.
     *
     * @override
     * @returns {Object}
     */
    getContext: function () {
        var state = this.model.get();
        return {
            graph_measure: state.measure,
            graph_mode: state.mode,
            graph_groupbys: state.groupedBy,
            // this parameter is not used anywher for now
            // the idea would be to seperate intervals from
            // fieldnames in groupbys. This could be done
            // in graph view only or everywhere but this is
            // a big refactoring.
            graph_intervalMapping: state.intervalMapping,
        };
    },
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
            var context = {
                measures: _.sortBy(_.pairs(_.omit(this.measures, '__count__')), function (x) { return x[1].string.toLowerCase(); }),
            };
            this.$buttons = $(qweb.render('GraphView.buttons', context));
            this.$measureList = this.$buttons.find('.o_graph_measures_list');
            this.$buttons.find('button').tooltip();
            this.$buttons.click(this._onButtonClick.bind(this));
            this._updateButtons();
            this.$buttons.appendTo($node);
            if (this.isEmbedded) {
                this._addGroupByMenu($node, this.groupableFields);
            }
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /*
     * override
     *
     * @private
     * @param {string[]} groupbys
     */
    _setGroupby: function (groupbys) {
        this.update({groupBy: groupbys});
    },

    /**
     * @todo remove this and directly calls update. Update should be overridden
     * and modified to call _updateButtons
     *
     * private
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
     * override
     *
     * @private
     */
    _update: function () {
        this._updateButtons();
        return this._super.apply(this, arguments);
    },
    /**
     * makes sure that the buttons in the control panel matches the current
     * state (so, correct active buttons and stuff like that)
     */
    _updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        var state = this.model.get();
        this.$buttons.find('.o_graph_button').removeClass('active');
        this.$buttons
            .find('.o_graph_button[data-mode="' + state.mode + '"]')
            .addClass('active');
        _.each(this.$measureList.find('.dropdown-item'), function (item) {
            var $item = $(item);
            $item.toggleClass('selected', $item.data('field') === state.measure);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Do what need to be done when a button from the control panel is clicked.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onButtonClick: function (event) {
        var $target = $(event.target);
        var field;
        if ($target.hasClass('o_graph_button')) {
            this._setMode($target.data('mode'));
        } else if ($target.parents('.o_graph_measures_list').length) {
            event.preventDefault();
            event.stopPropagation();
            field = $target.data('field');
            this._setMeasure(field);
        }
    },
});

return GraphController;

});
