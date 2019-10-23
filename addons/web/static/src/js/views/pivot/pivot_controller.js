odoo.define('web.PivotController', function (require) {
"use strict";
/**
 * Odoo Pivot Table Controller
 *
 * This class is the Controller for the pivot table view.  It has to coordinate
 * the actions coming from the search view (through the update method), from
 * the renderer, from the model, and from the control panel.
 *
 * It can display action buttons in the control panel, to select a different
 * measure, or to perform some other actions such as download/expand/flip the
 * view.
 */

var AbstractController = require('web.AbstractController');
var core = require('web.core');
var crash_manager = require('web.crash_manager');
var framework = require('web.framework');
var session = require('web.session');

var _t = core._t;
var QWeb = core.qweb;

var PivotController = AbstractController.extend({
    template: 'PivotView',
    events: {
        'click .o_pivot_header_cell_opened': '_onOpenHeaderClick',
        'click .o_pivot_header_cell_closed': '_onClosedHeaderClick',
        'click .o_pivot_field_menu a': '_onFieldMenuSelection',
        'click td': '_onCellClick',
        'click .o_pivot_measure_row': '_onMeasureRowClick',
    },
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.groupableFields a map from field name to field
     *   props
     * @param {boolean} params.enableLinking configure the pivot view to allow
     *   opening a list view by clicking on a cell with some data.
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);

        this.measures = params.measures;
        this.groupableFields = params.groupableFields;
        this.title = params.title;
        this.enableLinking = params.enableLinking;
        // views to use in the action triggered when a data cell is clicked
        this.views = params.views;
        this.lastHeaderSelected = null;
    },
    /**
     * @override
     */
    start: function () {
        this.$el.toggleClass('o_enable_linking', this.enableLinking);
        this.$fieldSelection = this.$('.o_field_selection');
        core.bus.on('click', this, function () {
            this.$fieldSelection.empty();
        });
        return this._super();
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$buttons) {
            // remove jquery's tooltip() handlers
            this.$buttons.find('button').off();
        }
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the current measures and groupbys, so we can restore the view
     * when we save the current state in the search view, or when we add it to
     * the dashboard.
     *
     * @override method from AbstractController
     * @returns {Object}
     */
    getContext: function () {
        var state = this.model.get();
        return {
            pivot_measures: state.measures,
            pivot_column_groupby: state.colGroupBys,
            pivot_row_groupby: state.rowGroupBys,
        };
    },
    /**
     * Render the buttons according to the PivotView.buttons template and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     *
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should
     *   be inserted. $node may be undefined, in which case the PivotView
     *   does nothing
     */
    renderButtons: function ($node) {
        if ($node) {
            var context = {measures: _.sortBy(_.pairs(_.omit(this.measures, '__count')), function (x) { return x[1].string.toLowerCase(); })};
            this.$buttons = $(QWeb.render('PivotView.buttons', context));
            this.$buttons.click(this._onButtonClick.bind(this));
            this.$buttons.find('button').tooltip();

            this.$buttons.appendTo($node);
            this._updateButtons();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Export the current pivot table data in a xls file. For this, we have to
     * serialize the current state, then call the server /web/pivot/export_xls.
     *
     * @private
     */
    _downloadTable: function () {
        var table = this.model.exportData();
        if(table.measure_row.length + 1 > 256) {
            crash_manager.show_message(_t("For Excel compatibility, data cannot be exported if there are more than 256 columns.\n\nTip: try to flip axis, filter further or reduce the number of measures."));
            framework.unblockUI();
            return;
        }
        framework.blockUI();
        table.title = this.title;
        session.get_file({
            url: '/web/pivot/export_xls',
            data: {data: JSON.stringify(table)},
            complete: framework.unblockUI,
            error: crash_manager.rpc_error.bind(crash_manager)
        });
    },
    /**
     * Render the field selection menu, to select a groupable field. We disable
     * already selected groupbys.
     *
     * @private
     * @param {number} top top coordinate where we have to render the menu
     * @param {number} left left coordinate for the menu
     */
    _renderFieldSelection: function (top, left) {
        var state = this.model.get({raw: true});
        var groupedFields = state.rowGroupBys
            .concat(state.colGroupBys)
            .map(function (f) { return f.split(':')[0];});

        var fields = _.chain(this.groupableFields)
            .pairs()
            .sortBy(function (f) { return f[1].string; })
            .map(function (f) {
                return [f[0], f[1], _.contains(groupedFields, f[0])];
            })
            .value();

        this.$fieldSelection.html(QWeb.render('PivotView.FieldSelection', {
            fields: fields
        }));

        var cssProps = {top: top};
        cssProps[_t.database.parameters.direction === 'rtl' ? 'right' : 'left'] =
            _t.database.parameters.direction === 'rtl' ? this.$el.width() - left : left;
        this.$fieldSelection.find('.dropdown-menu').first()
            .css(cssProps)
            .addClass('show');
    },
    /**
     * @private
     */
    _update: function () {
        this._updateButtons();
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     */
    _updateButtons: function () {
        if (!this.$buttons) {
            return;
        }
        var self = this;
        var state = this.model.get({raw: true});
        _.each(this.measures, function (measure, name) {
            var isSelected = _.contains(state.measures, name);
            self.$buttons.find('.dropdown-item[data-field="' + name + '"]')
                         .toggleClass('selected', isSelected);
        });
        var noDataDisplayed = !state.has_data || !state.measures.length;
        this.$buttons.find('.o_pivot_flip_button').prop('disabled', noDataDisplayed);
        this.$buttons.find('.o_pivot_expand_button').prop('disabled', noDataDisplayed);
        this.$buttons.find('.o_pivot_download').prop('disabled', noDataDisplayed);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This handler is called when the user clicked on a button in the control
     * panel.  We then have to react properly: it can either be a change in the
     * current measures, or a request to flip/expand/download data.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onButtonClick: function (event) {
        var $target = $(event.target);
        if ($target.hasClass('o_pivot_flip_button')) {
            this.model.flip();
            this.update({}, {reload: false});
        }
        if ($target.hasClass('o_pivot_expand_button')) {
            this.model
                    .expandAll()
                    .then(this.update.bind(this, {}, {reload: false}));
        }
        if ($target.parents('.o_pivot_measures_list').length) {
            var field = $target.data('field');
            event.preventDefault();
            event.stopPropagation();
            this.model
                    .toggleMeasure(field)
                    .then(this.update.bind(this, {}, {reload: false}));
        }
        if ($target.hasClass('o_pivot_download')) {
            this._downloadTable();
        }
    },
    /**
     * When the user clicks on a cell, and the view is configured to allow
     * 'linking' (with enableLinking), we want to open a list view with the
     * corresponding record.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onCellClick: function (event) {
        var $target = $(event.currentTarget);
        if ($target.hasClass('o_pivot_header_cell_closed') ||
            $target.hasClass('o_pivot_header_cell_opened') ||
            $target.hasClass('o_empty') ||
            $target.data('type') === 'variation' ||
            !this.enableLinking) {
            return;
        }
        var state = this.model.get(this.handle);
        var colDomain, rowDomain;
        if ($target.data('type') === 'comparisonData') {
            colDomain = this.model.getHeader($target.data('col_id')).comparisonDomain || [];
            rowDomain = this.model.getHeader($target.data('id')).comparisonDomain || [];
        } else {
            colDomain = this.model.getHeader($target.data('col_id')).domain || [];
            rowDomain = this.model.getHeader($target.data('id')).domain || [];
        }
        var context = _.omit(state.context, function (val, key) {
            return key === 'group_by' || _.str.startsWith(key, 'search_default_');
        });

        this.do_action({
            type: 'ir.actions.act_window',
            name: this.title,
            res_model: this.modelName,
            views: this.views,
            view_type: 'list',
            view_mode: 'list',
            target: 'current',
            context: context,
            domain: state.domain.concat(rowDomain, colDomain),
        });
    },
    /**
     * When we click on a closed header cell, we either want to open the
     * dropdown menu to select a new groupby level, or we want to open the
     * clicked header, if a corresponging groupby has already been selected.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onClosedHeaderClick: function (event) {
        var $target = $(event.target);
        var id = $target.data('id');
        var header = this.model.getHeader(id);
        var groupbys = header.root.groupbys;

        if (header.path.length - 1 < groupbys.length) {
            this.model
                .expandHeader(header, groupbys[header.path.length - 1])
                .then(this.update.bind(this, {}, {reload: false}));
        } else {
            this.lastHeaderSelected = id;
            var position = $target.position();
            var $parent = $target.offsetParent();
            var top = position.top + $target.height() + $parent.scrollTop();
            var left = position.left + event.offsetX + $parent.scrollLeft();
            this._renderFieldSelection(top, left);
            event.stopPropagation();
        }
    },
    /**
     * This handler is called when the user selects a field in the dropdown menu
     *
     * @private
     * @param {MouseEvent} event
     */
    _onFieldMenuSelection: function (event) {
        event.preventDefault();
        var $target = $(event.target);
        if ($target.hasClass('disabled')) {
            event.stopPropagation();
            return;
        }
        var field = $target.data('field');
        var interval = $target.data('interval');
        var header = this.model.getHeader(this.lastHeaderSelected);
        if (interval) {
            field = field + ':' + interval;
        }
        this.model
            .expandHeader(header, field)
            .then(this.update.bind(this, {}, {reload: false}));
    },
    /**
     * If the user clicks on a measure row, we can perform an in-memory sort
     *
     * @private
     * @param {MouseEvent} event
     */
    _onMeasureRowClick: function (event) {
        var $target = $(event.target);
        var col_id = $target.data('id');
        var measure = $target.data('measure');
        var isAscending = $target.hasClass('o_pivot_measure_row_sorted_asc');
        var dataType = $target.data('data_type');
        this.model.sortRows(col_id, measure, isAscending, dataType);
        this.update({}, {reload: false});
    },
    /**
     * This method is called when someone clicks on an open header.  When that
     * happens, we want to close the header, then redisplay the view.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onOpenHeaderClick: function (event) {
        event.preventDefault();
        event.stopImmediatePropagation();
        var headerID = $(event.target).data('id');
        this.model.closeHeader(headerID);
        this.update({}, {reload: false});
    },

});

return PivotController;

});
