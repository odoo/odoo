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
var framework = require('web.framework');
var session = require('web.session');

var _t = core._t;
var QWeb = core.qweb;

var PivotController = AbstractController.extend({
    contentTemplate: 'PivotView',
    events: {
        'click .o_pivot_field_menu a': '_onGroupByMenuSelection',
        'click .o_pivot_header_cell_closed': '_onClosedHeaderClick',
    },
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        close_group: '_onCloseGroup',
        open_view: '_onOpenView',
        sort_rows: '_onSortRows',
    }),
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.groupableFields a map from field names to field
     *   props
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);

        this.measures = params.measures;
        this.groupableFields = params.groupableFields;
        this.title = params.title;
        // views to use in the action triggered when a data cell is clicked
        this.views = params.views;
        this.groupSelected = null;
    },
    /**
     * @override
     */
    start: function () {
        this.$groupBySelection = this.$('.o_field_selection');
        core.bus.on('click', this, function () {
            this.$groupBySelection.empty();
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
    getOwnedQueryParams: function () {
        var state = this.model.get({raw: true});
        return {
            context: {
                pivot_measures: state.measures,
                pivot_column_groupby: state.colGroupBys,
                pivot_row_groupby: state.rowGroupBys,
            }
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
            var context = {
                measures: _.sortBy(_.pairs(_.omit(this.measures, '__count')), function (x) {
                    return x[1].string.toLowerCase();
                }),
            };
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
     * Force a reload before exporting to ensure to export up-to-date data.
     *
     * @private
     */
    _downloadTable: function () {
        var self = this;
        if (self.model.getTableWidth() > 256) {
            this.call('crash_manager', 'show_message', _t("For Excel compatibility, data cannot be exported if there are more than 256 columns.\n\nTip: try to flip axis, filter further or reduce the number of measures."));
            framework.unblockUI();
            return;
        }
        var table = self.model.exportData();
        table.title = self.title;
        session.get_file({
            url: '/web/pivot/export_xls',
            data: {data: JSON.stringify(table)},
            complete: framework.unblockUI,
            error: (error) => this.call('crash_manager', 'rpc_error', error),
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
    _renderGroupBySelection: function (top, left) {
        var state = this.model.get({raw: true});
        var groupedFields = state.rowGroupBys
            .concat(state.colGroupBys)
            .map(function (f) {
                return f.split(':')[0];
            });

        var fields = _.chain(this.groupableFields)
            .pairs()
            .sortBy(function (f) {
                return f[1].string;
            })
            .map(function (f) {
                return [f[0], f[1], _.contains(groupedFields, f[0])];
            })
            .value();

        this.$groupBySelection.html(QWeb.render('PivotView.GroupBySelection', {
            fields: fields
        }));

        var cssProps = {top: top};
        var isRTL = _t.database.parameters.direction === 'rtl';
        cssProps[isRTL ? 'right' : 'left'] = isRTL ? this.$el.width() - left : left;
        this.$groupBySelection.find('.dropdown-menu').first().css(cssProps).addClass('show');
    },
    /**
     * @override
     * @private
     */
    _startRenderer: function () {
        return this.renderer.appendTo(this.$('.o_pivot'));
    },
    /**
     * @override
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
        var noDataDisplayed = !state.hasData || !state.measures.length;
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
     * @param {MouseEvent} ev
     */
    _onButtonClick: function (ev) {
        var $target = $(ev.target);
        if ($target.hasClass('o_pivot_flip_button')) {
            this.model.flip();
            this.update({}, {reload: false});
        }
        if ($target.hasClass('o_pivot_expand_button')) {
            this.model.expandAll().then(this.update.bind(this, {}, {reload: false}));
        }
        if ($target.parents('.o_pivot_measures_list').length) {
            ev.preventDefault();
            ev.stopPropagation();
            var field = $target.data('field');
            this.model.toggleMeasure(field).then(this.update.bind(this, {}, {reload: false}));
        }
        if ($target.hasClass('o_pivot_download')) {
            this._downloadTable();
        }
    },
    /**
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onCloseGroup: function (ev) {
        this.model.closeGroup(ev.data.groupId, ev.data.type);
        this.update({}, {reload: false});
    },
    /**
     * When we click on a closed row (col) header, we either want to open the
     * dropdown menu to select a new field to add to rowGroupBys (resp. colGroupBys),
     * or we want to open the clicked header, if rowGroupBys (resp. colGroupBys)
     * has length strictly greater than header
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClosedHeaderClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        var $target = $(ev.target);
        var groupId = $target.data('groupId');
        var type = $target.data('type');

        var group = {
            rowValues: groupId[0],
            colValues: groupId[1],
            type: type
        };

        var state = this.model.get({raw: true});

        var groupValues = type === 'row' ? groupId[0] : groupId[1];
        var groupBys = type === 'row' ?
                        state.rowGroupBys :
                        state.colGroupBys;

        this.selectedGroup = group;
        if (groupValues.length < groupBys.length) {
            var groupBy = groupBys[groupValues.length];
            this.model
                .expandGroup(this.selectedGroup, groupBy)
                .then(this.update.bind(this, {}, {reload: false}));
        } else {
            var position = $target.position();
            var top = position.top + $target.height();
            var left = ev.clientX;
            this._renderGroupBySelection(top, left);
        }
    },
    /**
     * This handler is called when the user selects a groupby in the dropdown menu.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onGroupByMenuSelection: function (ev) {
        ev.preventDefault();
        var $target = $(ev.target);
        if ($target.hasClass('disabled')) {
            ev.stopPropagation();
            return;
        }

        var groupBy = $target.data('field');
        var interval = $target.data('interval');
        if (interval) {
            groupBy = groupBy + ':' + interval;
        }
        this.model.addGroupBy(groupBy, this.selectedGroup.type);
        this.model
            .expandGroup(this.selectedGroup, groupBy)
            .then(this.update.bind(this, {}, {reload: false}));
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onOpenView: function (ev) {
        ev.stopPropagation();
        var context = ev.data.context;
        var group = ev.data.group;
        var domain = this.model._getGroupDomain(group);

        this.do_action({
            type: 'ir.actions.act_window',
            name: this.title,
            res_model: this.modelName,
            views: this.views,
            view_mode: 'list',
            target: 'current',
            context: context,
            domain: domain,
        });
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onSortRows: function (ev) {
        this.model.sortRows(ev.data.sortedColumn);
        this.update({}, {reload: false});
    },
});

return PivotController;

});
