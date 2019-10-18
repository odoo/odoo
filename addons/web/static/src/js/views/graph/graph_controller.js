odoo.define('web.GraphController', function (require) {
"use strict";
/*---------------------------------------------------------
 * Odoo Graph view
 *---------------------------------------------------------*/

var core = require('web.core');
var AbstractController = require('web.AbstractController');
var GroupByMenuMixin = require('web.GroupByMenuMixin');

var qweb = core.qweb;

var GraphController = AbstractController.extend(GroupByMenuMixin,{
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
        GroupByMenuMixin.init.call(this);
        this._super.apply(this, arguments);
        this.measures = params.measures;
        // this parameter condition the appearance of a 'Group By'
        // button in the control panel owned by the graph view.
        this.isEmbedded = params.isEmbedded;

        // this parameter determines what is the list of fields
        // that may be used within the groupby menu available when
        // the view is embedded
        this.groupableFields = params.groupableFields;
    },
    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_graph_controller');
        return this._super.apply(this, arguments);
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
    getOwnedQueryParams: function () {
        var state = this.model.get();
        return {
            context: {
                graph_measure: state.measure,
                graph_mode: state.mode,
                graph_groupbys: state.groupBy,
            }
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
                this._addGroupByMenu($node, this.groupableFields).then(function(){
                    var groupByButton = $node.find('.o_dropdown_toggler_btn');
                    groupByButton.removeClass("o_dropdown_toggler_btn btn btn-secondary dropdown-toggle");
                    groupByButton.addClass("btn dropdown-toggle btn-outline-secondary");
                });
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
     * @param {string[]} groupBy
     */
    _setGroupby: function (groupBy) {
        this.update({groupBy: groupBy});
    },
    /**
     * @todo remove this and directly calls update. Update should be overridden
     * and modified to call _updateButtons
     *
     * @private
     *
     * @param {'pie'|'line'|'bar'} mode
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
     * @private
     *
     * @param {boolean} stacked
     */
    _toggleStackMode: function (stacked) {
        this.update({stacked: stacked});
        this._updateButtons();
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
        this.$buttons
            .find('.o_graph_button[data-mode="stack"]')
            .data('stacked', state.stacked)
            .toggleClass('active', state.stacked)
            .toggleClass('o_hidden', state.mode !== 'bar');
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
     * @param {MouseEvent} ev
     */
    _onButtonClick: function (ev) {
        var $target = $(ev.target);
        var field;
        if ($target.hasClass('o_graph_button')) {
            if (_.contains(['bar','line', 'pie'], $target.data('mode'))) {
                this._setMode($target.data('mode'));
            } else if ($target.data('mode') === 'stack') {
                this._toggleStackMode(!$target.data('stacked'));
            }
        } else if ($target.parents('.o_graph_measures_list').length) {
            ev.preventDefault();
            ev.stopPropagation();
            field = $target.data('field');
            this._setMeasure(field);
        }
    },
});

return GraphController;

});
