odoo.define('web.PivotRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var config = require('web.config');
var core = require('web.core');
var dataComparisonUtils = require('web.dataComparisonUtils');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;

var _t = core._t;

var PivotRenderer = AbstractRenderer.extend({
    tagName: 'table',
    className: 'table-hover table-sm table-bordered',
    events: _.extend({}, AbstractRenderer.prototype.events, {
        'click td.o_pivot_cell_value': '_onCellValueClicked',
        'click .o_pivot_header_cell_opened': '_onOpenHeaderClick',
        'click .o_pivot_measure_row': '_onSpecialRowClick',
        'click .o_pivot_origin_row': '_onSpecialRowClick',
        'mouseenter thead tr:last th': '_onMouseenterCell',
        'mouseenter tbody td': '_onMouseenterCell',
        'mouseleave thead tr:last th': '_onMouseleaveCell',
        'mouseleave tbody td': '_onMouseleaveCell',
    }),

    /**
     * @override
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     * @param {boolean} params.enableLinking configure the pivot view to allow
     *   opening a list view by clicking on a cell with some data.
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.enableLinking = params.enableLinking;
        this.fieldWidgets = params.widgets || {};
        this.paddingLeftHeaderTabWidth = config.device.isMobile ? 5 : 30;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string[]} groupBy list of 'fieldName[:period]'
     * @returns {string[]} list of fields label
     */
    _getGroupByLabels: function (groupBy) {
        var self = this;
        return _.map(groupBy, function (gb) {
            return self.state.fields[gb.split(':')[0]].string;
        });
    },
    /**
     * @override
     * @private
     * @returns {Promise}
     */
    _render: function () {
        var hasContent = this.state.hasData && this.state.measures.length;
        if (!hasContent) {
            // display the nocontent helper
            this._replaceElement(QWeb.render('View.NoContentHelper', {
                description: _t("Try to add some records, or make sure that there is at least " +
                    "one measure and no active filter in the search bar."),
            }));
            return this._super.apply(this, arguments);
        }

        this.renderElement(); // in case we come from no content helper
        this.$el.toggleClass('o_enable_linking', this.enableLinking);

        var $thead = $('<thead>');
        var $tbody = $('<tbody>');
        this._renderHeaders($thead);
        this._renderRows($tbody);
        this.$el.empty().append($thead).append($tbody);
        this.$('.o_pivot_header_cell_opened, .o_pivot_header_cell_closed').tooltip();

        return this._super.apply(this, arguments);
    },
    /**
     * @private
     * @param {jQuery} $thead
     */
    _renderHeaders: function ($thead) {
        // groupbyLabels is the list of col groupby fields label
        var groupbyLabels = this._getGroupByLabels(this.state.colGroupBys);

        this.state.table.headers.forEach(function (row, rowIndex) {
            var $tr = $('<tr>');
            row.forEach(function (cell) {
                var cellParams = {
                    text: cell.title,
                    colspan: cell.width,
                    rowspan: cell.height,
                    data: {
                        groupId: cell.groupId,
                        type: 'col',
                    }
                }
                var className;
                if (cell.measure) {
                    if (cell.originIndexes) {
                        cellParams.data.originIndexes = cell.originIndexes
                        className = 'o_pivot_origin_row';
                    } else {
                        className = 'o_pivot_measure_row';
                    }
                    className += ' text-muted';
                    if (cell.order) {
                        className += ' o_pivot_sort_order_' + cell.order;
                        if (cell.order === 'asc') {
                            cellParams['aria-sorted'] = 'ascending'
                        } else {
                            cellParams['aria-sorted'] = 'descending'
                        }
                    }
                    cellParams.data.measure = cell.measure;
                } else if ('isLeaf' in cell) {
                    if (rowIndex > 0) {
                        cellParams.title = groupbyLabels[rowIndex - 1];
                    }
                    className = 'o_pivot_header_cell' + (cell.isLeaf ? '_closed' : '_opened');
                }
                cellParams.class = className;
            
                $tr.append($('<th>', cellParams));
            });
            $thead.append($tr);
        });
    },
    /**
     * @private
     * @param {jQuery} $tbody
     */
    _renderRows: function ($tbody) {
        var self = this;

        // measureTypes is a mapping from measure fields to their field type,
        // with a special case for many2one fields which are mapped to the
        // 'integer' type (as their group_operator is 'count_distinct')
        var measureTypes = this.state.measures.reduce(
            function (acc, measureName) {
                var type = self.state.fields[measureName].type;
                acc[measureName] = type === 'many2one' ? 'integer' : type;
                return acc;
            },
            {}
        );

        // groupbyLabels is the list of row groupby fields label
        var groupbyLabels = this._getGroupByLabels(this.state.rowGroupBys);

        this.state.table.rows.forEach(function (row) {
            var $tr = $('<tr>');
            var paddingLeft = 5 + row.indent * self.paddingLeftHeaderTabWidth;
            $tr.append($('<th>', {
                text: row.title,
                title: row.indent > 0 ? groupbyLabels[row.indent - 1] : null,
                data: {
                    groupId: row.groupId,
                    type: 'row',
                },
                css: {
                    'padding-left': paddingLeft + 'px',
                },
                class: 'o_pivot_header_cell_' + (row.isLeaf ? 'closed' : 'opened'),
            }));

            row.subGroupMeasurements.forEach(function (measurement) {
                var cellParams = {
                    data: {
                        groupId: measurement.groupId,
                        originIndexes: measurement.originIndexes,
                    },
                    class: 'o_pivot_cell_value text-right',
                };
                if (measurement.isBold) {
                    cellParams.css = {
                        'font-weight': 'bold',
                    };
                }
                if (measurement.value !== undefined) {
                    var measure = measurement.measure;
                    var measureField = self.state.fields[measure];
                    var $value;
                    if (measurement.originIndexes.length > 1) {
                        $value = dataComparisonUtils.renderVariation(measurement.value, measureField);
                    } else {
                        var formatType = self.fieldWidgets[measure] || measureTypes[measure];
                        var formatter = field_utils.format[formatType];
                        $value = $('<div>', {
                            class: 'o_value',
                            html: formatter(measurement.value, measureField),
                        });
                    }
                    cellParams.html = $value;
                } else {
                    cellParams.class += ' o_empty'
                }
                $tr.append($('<td>', cellParams));
            });
            $tbody.append($tr);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When the user clicks on a non empty cell, and the view is configured to
     * allow 'linking' (with enableLinking), we want to open a list view with
     * the corresponding record.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onCellValueClicked: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        var $target = $(ev.currentTarget);
        if ($target.hasClass('o_empty') || !this.enableLinking) {
            return;
        }

        var context = _.omit(this.state.context, function (val, key) {
            return key === 'group_by' || _.str.startsWith(key, 'search_default_');
        });

        var groupId = $target.data('groupId');
        var originIndexes = $target.data('originIndexes');

        var group = {
            rowValues: groupId[0],
            colValues: groupId[1],
            originIndex: originIndexes[0]
        };

        this.trigger_up('open_view', {
            group: group,
            context: context,
        });
    },
    /**
     * Highlight the column when hovering a cell.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMouseenterCell: function (ev) {
        var index = $(ev.currentTarget).index();
        if ($(ev.currentTarget).is('th')) { // header cell
            index += 1; // increment by 1 to compensate the top left empty cell
        }
        this.$("td").filter(":nth-child(" + (index + 1) + ")").addClass("o_cell_hover");
    },
    /**
     * @private
     */
    _onMouseleaveCell: function () {
        this.$('.o_cell_hover').removeClass('o_cell_hover');
    },
    /**
     * This method is called when someone clicks on an open header.  When that
     * happens, we want to close the header, then redisplay the view.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onOpenHeaderClick: function (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();

        var $target = $(ev.target);
        var groupId = $target.data('groupId');
        var type = $target.data('type');

        this.trigger_up('close_group', {
            groupId: groupId,
            type: type,
        });
    },
    /**
     * If the user clicks on a measure or origin row, we perform an in-memory sort.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onSpecialRowClick: function (ev) {
        ev.preventDefault();
        ev.stopImmediatePropagation();

        var $target = $(ev.target);
        var groupId = $target.data('groupId');
        var measure = $target.data('measure');
        var originIndexes = $target.data('originIndexes');
        var isAscending = $target.hasClass('o_pivot_sort_order_asc');
        var order = isAscending ? 'desc' : 'asc';

        this.trigger_up('sort_rows', {
            sortedColumn: {
                groupId: groupId,
                measure: measure,
                order: order,
                originIndexes: originIndexes,
            }
        });
    },
});

return PivotRenderer;
});
