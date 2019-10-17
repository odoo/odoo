odoo.define('web.PivotRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var core = require('web.core');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;
var _t = core._t;

var PivotRenderer = AbstractRenderer.extend({
    tagName: 'table',
    className: 'table-hover table-sm table-bordered',
    events: _.extend({}, AbstractRenderer.prototype.events, {
        'hover td': '_onTdHover',
    }),

    /**
     * @overide
     *
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.compare = state.compare;
        this.fieldWidgets = params.widgets || {};
        this.timeRangeDescription = params.timeRangeDescription;
        this.comparisonTimeRangeDescription = params.comparisonTimeRangeDescription;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} state
     * @param {Object} params
     */
    updateState: function (state, params) {
        if (params.context !== undefined) {
            var timeRangeMenuData = params.context.timeRangeMenuData;
            if (timeRangeMenuData) {
                this.timeRangeDescription = timeRangeMenuData.timeRangeDescription;
                this.comparisonTimeRangeDescription = timeRangeMenuData.comparisonTimeRangeDescription;
            } else {
                this.timeRangeDescription = undefined;
                this.comparisonTimeRangeDescription = undefined;
            }
        }
        this.compare = state.compare;
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Used to determine whether or not to display the no content helper.
     *
     * @private
     * @returns {boolean}
     */
    _hasContent: function () {
        return this.state.has_data && this.state.measures.length;
    },
    /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        if (!this._hasContent()) {
            // display the nocontent helper
            this._replaceElement(QWeb.render('PivotView.nodata'));
            return this._super.apply(this, arguments);
        }

        if (!this.$el.is('table')) {
            // coming from the no content helper, so the root element has to be
            // re-rendered before rendering and appending its content
            this.renderElement();
        }
        var $fragment = $(document.createDocumentFragment());
        var $table = $('<table>').appendTo($fragment);
        var $thead = $('<thead>').appendTo($table);
        var $tbody = $('<tbody>').appendTo($table);
        var nbr_measures = this.state.measures.length;
        var nbrCols = (this.state.mainColWidth === 1) ?
            nbr_measures :
            (this.state.mainColWidth + 1) * nbr_measures;
        var i;
        if (this.compare) {
            for (i=0; i < 3 * nbrCols + 1; i++) {
                $table.prepend($('<col>'));
            }
        } else {
            for (i=0; i < nbrCols + 1; i++) {
                $table.prepend($('<col>'));
            }
        }
        this._renderHeaders($thead, this.state.headers, nbrCols);
        this._renderRows($tbody, this.state.rows);
        // todo: make sure the next line does something
        $table.find('.o_pivot_header_cell_opened,.o_pivot_header_cell_closed').tooltip();
        this.$el.html($table.contents());
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     * @param {jQueryElement} $thead
     * @param {jQueryElement} headers
     */
    _renderHeaders: function ($thead, headers, nbrCols) {
        var self = this;
        var i, j, cell, $row, $cell;
        var measure, dataType;
        var id, measureCellIds = [];

        var groupbyLabels = _.map(this.state.colGroupBys, function (gb) {
            return self.state.fields[gb.split(':')[0]].string;
        });

        for (i = 0; i < headers.length; i++) {
            $row = $('<tr>');
            for (j = 0; j < headers[i].length; j++) {
                cell = headers[i][j];
                if (i == 0 && j == 0) {
                    $cell = $('<th>')
                        .text(cell.title)
                        .attr('rowspan', cell.height + 1)
                        .attr('colspan', cell.width);
                } else {
                    $cell = $('<th>')
                        .text(cell.title)
                        .attr('rowspan', cell.height)
                        .attr('colspan', (cell.width && self.compare) ? 3 * cell.width : cell.width || (self.compare && cell.measure && 3));
                }
                if (i > 0) {
                    $cell.attr('title', groupbyLabels[i-1]);
                }
                if (cell.expanded !== undefined) {
                    $cell.addClass(cell.expanded ? 'o_pivot_header_cell_opened' : 'o_pivot_header_cell_closed');
                    $cell.data('id', cell.id);
                }
                if (cell.measure) {
                    measure = cell.measure;
                    measureCellIds.push(cell.id);
                    $cell.addClass('o_pivot_measure_row text-muted')
                        .text(this.state.fields[measure].string);
                    $cell.data('id', cell.id).data('measure', measure);
                    if (cell.id === this.state.sortedColumn.id &&
                        measure === this.state.sortedColumn.measure) {
                        $cell.addClass('o_pivot_measure_row_sorted_' + this.state.sortedColumn.order);
                        if (this.state.sortedColumn.order == 'asc') {
                            $cell.attr('aria-sorted', 'ascending');
                        } else {
                            $cell.attr('aria-sorted', 'descending');
                        }
                    }
                }
                $row.append($cell);

                $cell.toggleClass('d-none d-md-table-cell', (cell.expanded !== undefined) || (cell.measure !== undefined && j < headers[i].length - this.state.measures.length));
                if (cell.height > 1) {
                    $cell.css('padding', 0);
                }
            }
            $thead.append($row);
        }
        if (this.compare) {
            var colLabels = [this.timeRangeDescription, this.comparisonTimeRangeDescription, _t('Variation')];
            var dataTypes = ['data', 'comparisonData', 'variation'];
            $row = $('<tr>');
            for (i = 0; i < 3 * nbrCols; i++) {
                id = measureCellIds[~~(i / 3)];
                measure = this.state.measures[(~~(i / 3)) % this.state.measures.length];
                dataType = dataTypes[i % 3];
                $cell = $('<th>')
                    .addClass('o_pivot_measure_row text-muted')
                    .data('data_type', dataType)
                    .data('id', id)
                    .data('measure', measure)
                    .text(colLabels[i % 3])
                    .attr('rowspan', 1)
                    .attr('colspan', 1);
                if (dataType === this.state.sortedColumn.dataType &&
                    id === this.state.sortedColumn.id &&
                    measure === this.state.sortedColumn.measure) {
                    $cell.addClass('o_pivot_measure_row_sorted_' + this.state.sortedColumn.order);
                    if (this.state.sortedColumn.order === 'asc') {
                        $cell.attr('aria-sorted', 'ascending');
                    } else {
                        $cell.attr('aria-sorted', 'descending');
                    }
                }
                $row.append($cell);
            }
            $thead.append($row);
        }
    },
    /**
     * @private
     * @param {jQueryElement} $tbody
     * @param {jQueryElement} rows
     */
    _renderRows: function ($tbody, rows) {
        var self = this;
        var i, j, value, measure, name, formatter, $row, $cell, $header;
        var nbrMeasures = this.state.measures.length;
        var length = rows[0].values.length;
        var shouldDisplayTotal = this.state.mainColWidth > 1;

        var groupbyLabels = _.map(this.state.rowGroupBys, function (gb) {
            return self.state.fields[gb.split(':')[0]].string;
        });
        var measureTypes = this.state.measures.map(function (name) {
            var type = self.state.fields[name].type;
            return type === 'many2one' ? 'integer' : type;
        });
        for (i = 0; i < rows.length; i++) {
            $row = $('<tr>');
            $header = $('<td>')
                .text(rows[i].title)
                .data('id', rows[i].id)
                .css('padding-left', (5 + rows[i].indent * 30) + 'px')
                .addClass(rows[i].expanded ? 'o_pivot_header_cell_opened' : 'o_pivot_header_cell_closed');
            if (rows[i].indent > 0) $header.attr('title', groupbyLabels[rows[i].indent - 1]);
            $header.appendTo($row);
            for (j = 0; j < length; j++) {
                value = rows[i].values[j];
                name = this.state.measures[j % nbrMeasures];
                formatter = field_utils.format[this.fieldWidgets[name] || measureTypes[j % nbrMeasures]];
                measure = this.state.fields[name];
                if (this.compare) {
                    if (value instanceof Object) {
                        for (var origin in value) {
                            $cell = $('<td>')
                                .data('id', rows[i].id)
                                .data('col_id', rows[i].col_ids[Math.floor(j / nbrMeasures)])
                                .data('type' , origin)
                                .toggleClass('o_empty', false)
                                .addClass('o_pivot_cell_value text-right');
                            if (origin === 'data') {
                                $cell.append($('<div>', {class: 'o_value'}).html(formatter(
                                    value[origin],
                                    measure
                                )));
                            } else if (origin === 'comparisonData') {
                                $cell.append($('<div>', {class: 'o_comparison_value'}).html(formatter(
                                    value[origin],
                                    measure
                                )));
                            } else {
                                $cell.append($('<div>', {class: 'o_variation' + value[origin].signClass}).html(
                                    field_utils.format.percentage(
                                        value[origin].magnitude,
                                        measure
                                    )
                                ));
                            }
                            if (((j >= length - this.state.measures.length) && shouldDisplayTotal) || i === 0){
                                $cell.css('font-weight', 'bold');
                            }
                            $cell.toggleClass('d-none d-md-table-cell', j < length - nbrMeasures);
                            $row.append($cell);
                        }
                    } else {
                        for (var l=0; l < 3; l++) {
                            $cell = $('<td>')
                                .data('id', rows[i].id)
                                .toggleClass('o_empty', true)
                                .addClass('o_pivot_cell_value text-right');
                            $row.append($cell);
                        }
                    }
                } else {
                    $cell = $('<td>')
                                .data('id', rows[i].id)
                                .data('col_id', rows[i].col_ids[Math.floor(j / nbrMeasures)])
                                .toggleClass('o_empty', !value)
                                .addClass('o_pivot_cell_value text-right');
                    if (value !== undefined) {
                        $cell.append($('<div>', {class: 'o_value'}).html(formatter(value, measure)));
                    }
                    if (((j >= length - this.state.measures.length) && shouldDisplayTotal) || i === 0){
                        $cell.css('font-weight', 'bold');
                    }
                    $row.append($cell);

                    $cell.toggleClass('d-none d-md-table-cell', j < length - nbrMeasures);
                }
            }
            $tbody.append($row);
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onTdHover: function (event) {
        var $td = $(event.target);
        $td.closest('table').find('col:eq(' + $td.index()+')').toggleClass('hover');
    }

});

return PivotRenderer;
});
