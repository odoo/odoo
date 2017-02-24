odoo.define('web.PivotRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var field_utils = require('web.field_utils');

var PivotRenderer = AbstractRenderer.extend({
    tagName: 'table',
    className: 'table-hover table-condensed table-bordered',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        var $fragment = $(document.createDocumentFragment());
        var $table = $('<table>').appendTo($fragment);
        var $thead = $('<thead>').appendTo($table);
        var $tbody = $('<tbody>').appendTo($table);
        var nbr_measures = this.state.measures.length;
        var nbrCols = (this.state.mainColWidth === 1) ?
            nbr_measures :
            (this.state.mainColWidth + 1) * nbr_measures;
        for (var i=0; i < nbrCols + 1; i++) {
            $table.prepend($('<col>'));
        }
        this._renderHeaders($thead, this.state.headers);
        this._renderRows($tbody, this.state.rows);
        $table.on('hover', 'td', function () {
            $table.find('col:eq(' + $(this).index()+')').toggleClass('hover');
        });
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
    _renderHeaders: function ($thead, headers) {
        var self = this;
        var i, j, cell, $row, $cell;

        var groupbyLabels = _.map(this.state.colGroupBys, function (gb) {
            return self.state.fields[gb.split(':')[0]].string;
        });

        for (i = 0; i < headers.length; i++) {
            $row = $('<tr>');
            for (j = 0; j < headers[i].length; j++) {
                cell = headers[i][j];
                $cell = $('<th>')
                    .text(cell.title)
                    .attr('rowspan', cell.height)
                    .attr('colspan', cell.width);
                if (i > 0) {
                    $cell.attr('title', groupbyLabels[i-1]);
                }
                if (cell.expanded !== undefined) {
                    $cell.addClass(cell.expanded ? 'o_pivot_header_cell_opened' : 'o_pivot_header_cell_closed');
                    $cell.data('id', cell.id);
                }
                if (cell.measure) {
                    $cell.addClass('o_pivot_measure_row text-muted')
                        .text(this.state.fields[cell.measure].string);
                    $cell.data('id', cell.id).data('measure', cell.measure);
                    if (cell.id === this.state.sortedColumn.id && cell.measure === this.state.sortedColumn.measure) {
                        $cell.addClass('o_pivot_measure_row_sorted_' + this.state.sortedColumn.order);
                    }
                }
                $row.append($cell);

                $cell.toggleClass('hidden-xs', (cell.expanded !== undefined) || (cell.measure !== undefined && j < headers[i].length - this.state.measures.length));
                if (cell.height > 1) {
                    $cell.css('padding', 0);
                }
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
        var i, j, value, measure, name, $row, $cell, $header;
        var nbrMeasures = this.state.measures.length;
        var length = rows[0].values.length;
        var shouldDisplayTotal = this.state.mainColWidth > 1;

        var groupbyLabels = _.map(this.state.rowGroupBys, function (gb) {
            return self.state.fields[gb.split(':')[0]].string;
        });
        var measureTypes = this.state.measures.map(function (name) {
            return self.state.fields[name].type;
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
                if (value !== undefined) {
                    name = this.state.measures[j % nbrMeasures];
                    measure = this.state.fields[name];
                    value = field_utils.format[measureTypes[j % nbrMeasures]](value, measure);
                }
                $cell = $('<td>')
                            .data('id', rows[i].id)
                            .data('col_id', rows[i].col_ids[Math.floor(j / nbrMeasures)])
                            .toggleClass('o_empty', !value)
                            .text(value)
                            .addClass('o_pivot_cell_value text-right');
                if (((j >= length - this.state.measures.length) && shouldDisplayTotal) || i === 0){
                    $cell.css('font-weight', 'bold');
                }
                $row.append($cell);

                $cell.toggleClass('hidden-xs', j < length - nbrMeasures);
            }
            $tbody.append($row);
        }
    },

});

return PivotRenderer;
});
