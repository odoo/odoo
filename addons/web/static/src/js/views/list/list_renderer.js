odoo.define('web.ListRenderer', function (require) {
"use strict";

var BasicRenderer = require('web.BasicRenderer');
var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');
var field_registry = require('web.field_registry');
var field_utils = require('web.field_utils');
var session = require('web.session');
var utils = require('web.utils');

var _t = core._t;

// Allowed decoration on the list's rows: bold, italic and bootstrap semantics classes
var DECORATIONS = [
    'decoration-bf',
    'decoration-it',
    'decoration-danger',
    'decoration-info',
    'decoration-muted',
    'decoration-primary',
    'decoration-success',
    'decoration-warning'
];

var FIELD_CLASSES = {
    'monetary': 'o_list_number',
    'text': 'o_list_text',
    'float': 'o_list_number',
};

var ListRenderer = BasicRenderer.extend({
    className: 'table-responsive',
    events: {
        'click tbody tr': '_onRowClicked',
        'click tbody .o_list_record_selector': '_onSelectRecord',
        'click thead th.o_column_sortable': '_onSortColumn',
        'click .o_group_header': '_onToggleGroup',
        'click thead .o_list_record_selector input': '_onToggleSelection',
    },
    /**
     * @constructor
     * @param {Widget} parent
     * @param {any} state
     * @param {Object} params
     * @param {boolean} params.hasSelectors
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        var self = this;
        this.hasHandle = false;
        this.columns = _.reject(this.arch.children, function (c) {
            if (c.attrs.invisible === '1') {
                return true;
            }
            var modifiers = JSON.parse(c.attrs.modifiers || '{}');
            if (modifiers.tree_invisible) {
                return true;
            }
            if (c.attrs.widget === 'handle') {
                self.hasHandle = true;
            }
            var keys = ['list.' + c.attrs.widget, c.attrs.widget];
            c.Widget = field_registry.getAny(keys);
            c.modifiers = modifiers;
            return false;
        });
        this.rowDecorations = _.chain(this.arch.attrs)
            .pick(function (value, key) {
                return DECORATIONS.indexOf(key) >= 0;
            }).mapObject(function (value) {
                return py.parse(py.tokenize(value));
            }).value();
        this.hasSelectors = params.hasSelectors;
        this.selection = [];
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This method does a in-memory computation of the aggregate values, for
     * each columns that corresponds to a numeric field with a proper aggregate
     * function.
     *
     * The result of these computations is stored in the 'aggregate' key of each
     * column of this.columns.  This will be then used by the _renderFooter
     * method to display the appropriate amount.
     */
    _computeAggregates: function () {
        var self = this;
        var data = [];
        if (this.selection.length) {
            utils.traverse_records(this.state, function (record) {
                if (_.contains(self.selection, record.id)) {
                    data.push(record); // find selected records
                }
            });
        } else {
            data = this.state.data;
        }
        if (data.length === 0) {
            return;
        }

        _.each(this.columns, function (column) {
            var attrs = column.attrs;
            var field = self.state.fields[attrs.name];
            if (!field) {
                return;
            }
            var type = field.type;
            if (type !== 'integer' && type !== 'float' && type !== 'monetary') {
                return;
            }
            var func = (attrs.sum && 'sum') || (attrs.avg && 'avg') ||
                       (attrs.max && 'max') || (attrs.min && 'min');
            if (func) {
                var count = 0;
                var aggregate_value = (func === 'max') ? -Infinity : (func === 'min') ? Infinity : 0;
                _.each(data, function (d) {
                    count += 1;
                    var value = (d.type === 'record') ? d.data[attrs.name] : d.aggregateValues[attrs.name];
                    if (func === 'avg') {
                        aggregate_value += value;
                    } else if (func === 'sum') {
                        aggregate_value += value;
                    } else if (func === 'max') {
                        aggregate_value = Math.max(aggregate_value, value);
                    } else if (func === 'min') {
                        aggregate_value = Math.min(aggregate_value, value);
                    }
                });
                if (func === 'avg') {
                    aggregate_value = aggregate_value / count;
                }
                column.aggregate = {
                    help: attrs[func],
                    value: aggregate_value,
                };
            }
        });
    },
    /**
     * Each line can be decorated according to a few simple rules. The arch
     * description of the list may have one of the decoration-X attribute with
     * a domain as value.  Then, for each record, we check if the domain matches
     * the record, and add the text-X css class to the element.  This method is
     * concerned with the computation of the list of css classes for a given
     * record.
     *
     * @param {Object} record a basic model record
     * @returns {string[]} a list of css classes
     */
    _computeDecorationClassNames: function (record) {
        var context = _.extend({}, record.data, {
            uid: session.uid,
            current_date: moment().format('YYYY-MM-DD')
            // TODO: time, datetime, relativedelta
        });
        return _.chain(this.rowDecorations)
            .pick(function (expr) {
                return py.PY_isTrue(py.evaluate(expr, context));
            }).map(function (expr, decoration) {
                return decoration.replace('decoration', 'text');
            }).value();
    },
    /**
     * When a list view is grouped, we need to display the name of each group in
     * the 'title' row.  This is the purpose of this method.
     *
     * @param {any} value
     * @param {Object} field a field description
     * @returns {string}
     */
    _formatValue: function (value, field) {
        if (field && field.type === 'selection') {
            var choice = _.find(field.selection, function (c) {
                return c[0] === value;
            });
            return choice[1];
        }
        return value || _t('Undefined');
    },
    /**
     * return the number of visible columns.  Note that this number depends on
     * the state of the renderer.  For example, in editable mode, it could be
     * one more that in non editable mode, because there may be a visible 'trash
     * icon'.
     *
     * @returns {number}
     */
    _getNumberOfCols: function () {
        var n = this.columns.length;
        return this.hasSelectors ? n+1 : n;
    },
    /**
     * Determine if a given cell is invisible.  A cell is considered invisible
     * if there is an 'invisible' attr, with a matching domain.
     *
     * @param {Object} record a basic model record
     * @param {Object} node a node object (from the arch)
     * @returns {boolean}
     */
    _isInvisible: function (record, node) {
        if ('invisible' in node.modifiers) {
            var fieldValues = this._getFieldValues(record);
            return new Domain(node.modifiers.invisible).compute(fieldValues);
        }
        return false;
    },
    /**
     * Render a list of <td>, with aggregates if available.  It can be displayed
     * in the footer, or for each open groups.
     *
     * @param {any} aggregate_values
     * @returns {jQueryElement[]} a list of <td> with the aggregate values
     */
    _renderAggregateCells: function (aggregate_values) {
        var self = this;
        return _.map(this.columns, function (column) {
            var $cell = $('<td>');
            if (column.attrs.name in aggregate_values) {
                var field = self.state.fields[column.attrs.name];
                var value = aggregate_values[column.attrs.name].value;
                var help = aggregate_values[column.attrs.name].help;
                var formattedValue = field_utils['format_' + field.type](value, field, {});
                $cell.addClass('o_list_number').attr('title', help).html(formattedValue);
            }
            return $cell;
        });
    },
    /**
     * Render the main body of the table, with all its content.  Note that it
     * has been decided to always render at least 4 rows, even if we have less
     * data.  The reason is that lists with 0 or 1 lines don't really look like
     * a table.
     *
     * @returns {jQueryElement} a jquery element <tbody>
     */
    _renderBody: function () {
        var $rows = this._renderRows();
        while ($rows.length < 4) {
            $rows.push(this._renderEmptyRow());
        }
        return $('<tbody>').append($rows);
    },
    /**
     * Render a cell for the table.  For most cells, we only want to display the
     * formatted value, with some appropriate css class.  However, when the
     * node was explicitely defined with a 'widget' attribute, then we
     * instantiate the corresponding widget.
     *
     * @param {Object} record
     * @param {Object} node
     * @returns {jQueryElement} a <td> element
     */
    _renderBodyCell: function (record, node) {
        var self = this;
        var $td = $('<td>');
        if (this._isInvisible(record, node)) {
            return $td;
        }
        if (node.tag === 'button') {
            var $button = $('<button type="button">').addClass('o_icon_button');
            $button.append($('<i>').addClass('fa').addClass(node.attrs.icon))
                .prop('title', node.attrs.string)
                .click(function (e) {
                    e.stopPropagation();
                    self.trigger_up('list_button_clicked', {
                        attrs: node.attrs,
                        record: record,
                    });
                });
            $td.append($button);
            $td.addClass('o_list_button').click(function (e) {
                // prevent opening or editing the record on cell click
                e.stopPropagation();
            });
            return $td;
        }
        var field = this.state.fields[node.attrs.name];
        var value = record.data[node.attrs.name];
        if (node.Widget) {
            var widget = new node.Widget(this, node.attrs.name, record, {
                mode: 'readonly',
            });
            widget.appendTo($td);
            $td.addClass('o_' + node.attrs.widget + '_cell');
            return $td;
        }
        $td.addClass(FIELD_CLASSES[field.type]);
        var formatted_value = field_utils.format_field(value, field, { data: record.data });
        return $td.html(formatted_value);
    },
    /**
     * Render a complete empty row.  This is used to fill in the blanks when we
     * have less than 4 lines to display.
     *
     * @returns {jQueryElement} a <tr> element
     */
    _renderEmptyRow: function () {
        var $td = $('<td>&nbsp;</td>').attr('colspan', this._getNumberOfCols());
        return $('<tr>').append($td);
    },
    /**
     * Render the footer.  It is a <tfoot> with a single row, containing all
     * aggregates, if applicable.
     *
     * @param {boolean} isGrouped if the view is grouped, we have to add an
     *   extra <td>
     * @returns {jQueryElement} a <tfoot> element
     */
    _renderFooter: function (isGrouped) {
        var aggregates = {};
        _.each(this.columns, function (column) {
            if ('aggregate' in column) {
                aggregates[column.attrs.name] = column.aggregate;
            }
        });
        var $cells = this._renderAggregateCells(aggregates);
        if (isGrouped) {
            $cells.unshift($('<td>'));
        }
        if (this.hasSelectors) {
            $cells.unshift($('<td>'));
        }
        return $('<tfoot>').append($('<tr>').append($cells));
    },
    /**
     * Render the row that represent a group
     *
     * @param {Object} group
     * @returns {jQueryElement} a <tr> element
     */
    _renderGroupRow: function (group) {
        var aggregate_values = _.mapObject(group.aggregateValues, function (value) {
            return { value: value };
        });
        var $cells = this._renderAggregateCells(aggregate_values);
        if (this.hasSelectors) {
            $cells.unshift($('<td>'));
        }
        var field = this.state.fields[group.groupedBy[0]];
        var name = this._formatValue(group.value, field);
        var $th = $('<th>')
                    .addClass('o_group_name')
                    .text(name + ' (' + group.count + ')');
        if (group.count > 0) {
            var $arrow = $('<span style="padding-right: 5px;">')
                            .addClass('fa')
                            .toggleClass('fa-caret-right', !group.isOpen)
                            .toggleClass('fa-caret-down', group.isOpen);
            $th.prepend($arrow);
        }
        return $('<tr>')
                    .addClass('o_group_header')
                    .data('group', group)
                    .append($th)
                    .append($cells);
    },
    /**
     * Render all groups in the view.  We assume that the view is in grouped
     * mode.
     *
     * Note that each group is rendered inside a <tbody>, which contains a group
     * row, then possibly a bunch of rows for each record.
     *
     * @returns {jQueryElement[]} a list of <tbody>
     */
    _renderGroups: function () {
        var self = this;
        var result = [];
        var $tbody = $('<tbody>');
        _.each(this.state.data, function (group) {
            if (!$tbody) {
                $tbody = $('<tbody>');
            }
            $tbody.append(self._renderGroupRow(group));
            if (group.data.length) {
                result.push($tbody);
                var $records = _.map(group.data, function (record) {
                    return self._renderRow(record).prepend($('<td>'));
                });
                result.push($('<tbody>').append($records));
                $tbody = null;
            }
        });
        if ($tbody) {
            result.push($tbody);
        }
        return result;
    },
    /**
     * Render the main header for the list view.  It is basically just a <thead>
     * with the name of each fields
     *
     * @param {boolean} isGrouped
     * @returns {jQueryElement} a <thead> element
     */
    _renderHeader: function (isGrouped) {
        var $tr = $('<tr>')
                .append(_.map(this.columns, this._renderHeaderCell.bind(this)));
        if (this.hasSelectors) {
            $tr.prepend(this._renderSelector('th'));
        }
        if (isGrouped) {
            $tr.prepend($('<th>').html('&nbsp;'));
        }
        return $('<thead>').append($tr);
    },
    /**
     * Render a single <th> with the informations for a column. If it is not a
     * field, the th will be empty. Otherwise, it will contains all relevant
     * information for the field.
     *
     * @param {Object} node
     * @returns {jQueryElement} a <th> element
     */
    _renderHeaderCell: function (node) {
        var order = this.state.orderedBy;
        var isNodeSorted = order[0] && order[0].name === node.attrs.name;
        var field = this.state.fields[node.attrs.name];
        var $th = $('<th>');
        if (!field) {
            return $th;
        }
        var description;
        if (node.Widget) {
            description = node.Widget.prototype.description;
        }
        if (description === undefined) {
            description = node.attrs.string || field.string;
        }
        $th
            .text(description)
            .data('name', node.attrs.name)
            .toggleClass('o-sort-down', isNodeSorted ? !order[0].asc : false)
            .toggleClass('o-sort-up', isNodeSorted ? order[0].asc : false)
            .addClass(field.sortable && 'o_column_sortable');

        if (field.type === 'float' || field.type === 'monetary') {
            $th.css({textAlign: 'right'});
        }

        if (config.debug) {
            var fieldDescr = {
                field: field,
                name: node.attrs.name,
                string: description || node.attrs.name,
                record: this.state,
                attrs: node.attrs,
            };
            this._addFieldTooltip(fieldDescr, $th);
        }
        return $th;
    },
    /**
     * Render a row, corresponding to a record.
     *
     * @param {Object} record
     * @returns {jQueryElement} a <tr> element
     */
    _renderRow: function (record) {
        var decorations = this._computeDecorationClassNames(record);
        var $cells = _.map(this.columns, this._renderBodyCell.bind(this, record));
        var $tr = $('<tr class="o_data_row">')
                    .data('id', record.id)
                    .addClass(decorations.length && decorations.join(' '))
                    .append($cells);
        if (this.hasSelectors) {
            $tr.prepend(this._renderSelector('td'));
        }
        return $tr;
    },
    /**
     * Render all rows. This method should only called when the view is not
     * grouped.
     *
     * @returns {jQueryElement[]} a list of <tr>
     */
    _renderRows: function () {
        return _.map(this.state.data, this._renderRow.bind(this));
    },
    _renderSelector: function (tag) {
        var $content = $('<div class="o_checkbox"><input type="checkbox"><span/></div>');
        return $('<' + tag + ' width="1">')
                    .addClass('o_list_record_selector')
                    .append($content);
    },
    /**
     * @override
     * returns {Deferred}
     */
    _renderView: function () {
        var self = this;
        var $table = $('<table>').addClass('o_list_view table table-condensed table-striped');
        this.$el.empty().append($table);
        var is_grouped = !!this.state.groupedBy.length;
        this._computeAggregates();
        $table.toggleClass('o_list_view_grouped', is_grouped);
        $table.toggleClass('o_list_view_ungrouped', !is_grouped);
        if (is_grouped) {
            $table
                .append(this._renderHeader(true))
                .append(this._renderGroups())
                .append(this._renderFooter(true));
        } else {
            $table
                .append(this._renderHeader())
                .append(this._renderBody())
                .append(this._renderFooter());
        }
        if (this.selection.length) {
            var $checked_rows = this.$('tr').filter(function (index, el) {
                return _.contains(self.selection, $(el).data('id'));
            });
            $checked_rows.find('.o_list_record_selector input').prop('checked', true);
        }
        return this._super();
    },
    _updateSelection: function () {
        var $selectedRows = this.$('tbody .o_list_record_selector input:checked')
                                .closest('tr');
        this.selection = _.map($selectedRows, function (row) {
            return $(row).data('id');
        });
        this.trigger_up('selection_changed', { selection: this.selection });
        this._computeAggregates();
        this.$('tfoot').replaceWith(this._renderFooter(!!this.state.groupedBy.length));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @param {MouseEvent} event
     */
    _onRowClicked: function (event) {
        var id = $(event.currentTarget).data('id');
        if (id) {
            this.trigger_up('open_record', {id:id, target: event.target});
        }
    },
    /**
     * @param {MouseEvent} event
     */
    _onSelectRecord: function (event) {
        event.stopPropagation();
        this._updateSelection();
        if (!$(event.currentTarget).find('input').prop('checked')) {
            this.$('thead .o_list_record_selector input').prop('checked', false);
        }
    },
    /**
     * @param {MouseEvent} event
     */
    _onSortColumn: function (event) {
        var name = $(event.currentTarget).data('name');
        this.trigger_up('toggle_column_order', {id: this.state.id, name: name});
    },
    /**
     * @param {MouseEvent} event
     */
    _onToggleGroup: function (event) {
        var group = $(event.currentTarget).data('group');
        if (group.count) {
            this.trigger_up('toggle_group', {group: group});
        }
    },
    _onToggleSelection: function (event) {
        var checked = $(event.currentTarget).prop('checked') || false;
        this.$('tbody .o_list_record_selector input').prop('checked', checked);
        this._updateSelection();
    },
});

return ListRenderer;

});
