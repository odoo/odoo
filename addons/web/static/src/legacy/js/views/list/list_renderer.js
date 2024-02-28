/** @odoo-module alias=web.ListRenderer **/

import BasicRenderer from 'web.BasicRenderer';
import { ComponentWrapper } from 'web.OwlCompatibility';
import config from 'web.config';
import core from 'web.core';
import dom from 'web.dom';
import field_utils from 'web.field_utils';
import Pager from 'web.Pager';
import utils from 'web.utils';
import viewUtils from 'web.viewUtils';

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
    char: 'o_list_char',
    float: 'o_list_number',
    integer: 'o_list_number',
    monetary: 'o_list_number',
    text: 'o_list_text',
    many2one: 'o_list_many2one',
};

var ListRenderer = BasicRenderer.extend({
    className: 'o_legacy_list_view',
    events: {
        "mousedown": "_onMouseDown",
        "click .o_optional_columns_dropdown .dropdown-item": "_onToggleOptionalColumn",
        "click .o_optional_columns_dropdown_toggle": "_onToggleOptionalColumnDropdown",
        'click tbody tr': '_onRowClicked',
        'change tbody .o_list_record_selector': '_onSelectRecord',
        'click thead th.o_column_sortable': '_onSortColumn',
        'click .o_list_record_selector': '_onToggleCheckbox',
        'click .o_group_header': '_onToggleGroup',
        'change thead .o_list_record_selector input': '_onToggleSelection',
        'keypress thead tr td': '_onKeyPress',
        'keydown td': '_onKeyDown',
        'keydown th': '_onKeyDown',
    },
    sampleDataTargets: [
        '.o_data_row',
        '.o_group_header',
        '.o_list_table > tfoot',
        '.o_list_table > thead .o_list_record_selector',
    ],
    /**
     * @constructor
     * @param {Widget} parent
     * @param {any} state
     * @param {Object} params
     * @param {boolean} params.hasSelectors
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this._preprocessColumns();
        this.columnInvisibleFields = params.columnInvisibleFields || {};
        this.rowDecorations = this._extractDecorationAttrs(this.arch);
        this.fieldDecorations = {};
        for (const field of this.arch.children.filter(c => c.tag === 'field')) {
            const decorations = this._extractDecorationAttrs(field);
            this.fieldDecorations[field.attrs.name] = decorations;
        }
        this.hasSelectors = params.hasSelectors;
        this.selection = params.selectedRecords || [];
        this.pagers = []; // instantiated pagers (only for grouped lists)
        this.isGrouped = this.state.groupedBy.length > 0;
        this.groupbys = params.groupbys;
        this.no_open = params.no_open;
    },
    /**
     * Compute columns visilibity. This can't be done earlier as we need the
     * controller to respond to the load_optional_fields call of processColumns.
     *
     * @override
     */
    willStart: function () {
        this._processColumns(this.columnInvisibleFields);
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Order to focus to be given to the content of the current view
     *
     * @override
     */
    giveFocus: function () {
        this.$('th:eq(0) input, th:eq(1)').first().focus();
    },
    /**
     * @override
     */
    updateState: function (state, params) {
        this._setState(state);
        this.isGrouped = this.state.groupedBy.length > 0;
        this.columnInvisibleFields = params.columnInvisibleFields || {};
        this._processColumns(this.columnInvisibleFields);
        if (params.selectedRecords) {
            this.selection = params.selectedRecords;
        }
        return this._super.apply(this, arguments);
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
     *
     * @private
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

        _.each(this.columns, this._computeColumnAggregates.bind(this, data));
    },
    /**
     * Compute the aggregate values for a given column and a set of records.
     * The aggregate values are then written, if applicable, in the 'aggregate'
     * key of the column object.
     *
     * @private
     * @param {Object[]} data a list of selected/all records
     * @param {Object} column
     */
    _computeColumnAggregates: function (data, column) {
        var attrs = column.attrs;
        var field = this.state.fields[attrs.name];
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
            var aggregateValue = 0;
            if (func === 'max') {
                aggregateValue = -Infinity;
            } else if (func === 'min') {
                aggregateValue = Infinity;
            }
            _.each(data, function (d) {
                var value = (d.type === 'record') ? d.data[attrs.name] : d.aggregateValues[attrs.name];
                if (Number(value) !== value) {
                    return;
                }
                count += 1;
                if (func === 'avg') {
                    aggregateValue += value;
                } else if (func === 'sum') {
                    aggregateValue += value;
                } else if (func === 'max') {
                    aggregateValue = Math.max(aggregateValue, value);
                } else if (func === 'min') {
                    aggregateValue = Math.min(aggregateValue, value);
                }
            });
            if (func === 'avg') {
                aggregateValue = count ? aggregateValue / count : aggregateValue;
            }
            if (count) {
                column.aggregate = {
                    help: attrs[func],
                    value: aggregateValue,
                };
            } else {
                delete column.aggregate;
            }
        }
    },
    /**
     * Extract the decoration attributes (e.g. decoration-danger) of a node. The
     * condition is processed such that it is ready to be evaluated.
     *
     * @private
     * @param {Object} node the <tree> or a <field> node
     * @returns {Object}
     */
    _extractDecorationAttrs: function (node) {
        const decorations = {};
        for (const [key, expr] of Object.entries(node.attrs)) {
            if (DECORATIONS.includes(key)) {
                let cssClass;
                if (key === 'decoration-bf') {
                    cssClass = 'fw-bold';
                } else if (key === 'decoration-it') {
                    cssClass = 'fst-italic';
                } else {
                    cssClass = key.replace('decoration', 'text');
                }
                decorations[cssClass] = py.parse(py.tokenize(expr));
            }
        }
        return decorations;
    },
    /**
     *
     * @private
     * @param {jQuery} $cell
     * @param {string} direction
     * @param {integer} colIndex
     * @returns {jQuery|null}
     */
    _findConnectedCell: function ($cell, direction, colIndex) {
        var $connectedRow = $cell.closest('tr')[direction]('tr');

        if (!$connectedRow.length) {
            // Is there another group ? Look at our parent's sibling
            // We can have th in tbody so we can't simply look for thead
            // if cell is a th and tbody instead
            var tbody = $cell.closest('tbody, thead');
            var $connectedGroup = tbody[direction]('tbody, thead');
            if ($connectedGroup.length) {
                // Found another group
                var $connectedRows = $connectedGroup.find('tr');
                var rowIndex;
                if (direction === 'prev') {
                    rowIndex = $connectedRows.length - 1;
                } else {
                    rowIndex = 0;
                }
                $connectedRow = $connectedRows.eq(rowIndex);
            } else {
                // End of the table
                return;
            }
        }

        var $connectedCell;
        if ($connectedRow.hasClass('o_group_header')) {
            $connectedCell = $connectedRow.children();
            this.currentColIndex = colIndex;
        } else if ($connectedRow.has('td.o_group_field_row_add').length) {
            $connectedCell = $connectedRow.find('.o_group_field_row_add');
            this.currentColIndex = colIndex;
        } else {
            var connectedRowChildren = $connectedRow.children();
            if (colIndex === -1) {
                colIndex = connectedRowChildren.length - 1;
            }
            $connectedCell = connectedRowChildren.eq(colIndex);
        }

        return $connectedCell;
    },
    /**
     * return the number of visible columns.  Note that this number depends on
     * the state of the renderer.  For example, in editable mode, it could be
     * one more that in non editable mode, because there may be a visible 'trash
     * icon'.
     *
     * @private
     * @returns {integer}
     */
    _getNumberOfCols: function () {
        var n = this.columns.length;
        return this.hasSelectors ? n + 1 : n;
    },
    /**
     * Returns the local storage key for stored enabled optional columns
     *
     * @private
     * @returns {string}
     */
    _getOptionalColumnsStorageKeyParts: function () {
        var self = this;
        return {
            fields: _.map(this.state.fieldsInfo[this.viewType], function (_, fieldName) {
                return {name: fieldName, type: self.state.fields[fieldName].type};
            }),
        };
    },
    /**
     * Returns the jQuery node used to update the selection
     *
     * @private
     * @return {jQuery}
     */
    _getSelectableRecordCheckboxes: function () {
        return this.$('tbody .o_list_record_selector input:visible:not(:disabled)');
    },
    /**
     * Adjacent buttons (in the arch) are displayed in a single column. This
     * function iterates over the arch's nodes and replaces "button" nodes by
     * "button_group" nodes, with a single "button_group" node for adjacent
     * "button" nodes. A "button_group" node has a "children" attribute
     * containing all "button" nodes in the group.
     *
     * @private
     */
    _groupAdjacentButtons: function () {
        const children = [];
        let groupId = 0;
        let buttonGroupNode = null;
        for (const c of this.arch.children) {
            if (c.tag === 'button') {
                if (!buttonGroupNode) {
                    buttonGroupNode = {
                        tag: 'button_group',
                        children: [c],
                        attrs: {
                            name: `button_group_${groupId++}`,
                            modifiers: {},
                        },
                    };
                    children.push(buttonGroupNode);
                } else {
                    buttonGroupNode.children.push(c);
                }
            } else {
                buttonGroupNode = null;
                children.push(c);
            }
        }
        this.arch.children = children;
    },
    /**
     * Processes arch's child nodes for the needs of the list view:
     *   - detects oe_read_only/oe_edit_only classnames
     *   - groups adjacent buttons in a single column.
     * This function is executed only once, at initialization.
     *
     * @private
     */
    _preprocessColumns: function () {
        this._processModeClassNames();
        this._groupAdjacentButtons();

        // set as readOnly (resp. editOnly) button groups containing only
        // readOnly (resp. editOnly) buttons, s.t. no column is rendered
        this.arch.children.filter(c => c.tag === 'button_group').forEach(c => {
            c.attrs.editOnly = c.children.every(n => n.attrs.editOnly);
            c.attrs.readOnly = c.children.every(n => n.attrs.readOnly);
        });
    },
    /**
     * Removes the columns which should be invisible. This function is executed
     * at each (re-)rendering of the list.
     *
     * @param  {Object} columnInvisibleFields contains the column invisible modifier values
     */
    _processColumns: function (columnInvisibleFields) {
        var self = this;
        this.handleField = null;
        this.columns = [];
        this.optionalColumns = [];
        this.optionalColumnsEnabled = [];
        var storedOptionalColumns;
        this.trigger_up('load_optional_fields', {
            keyParts: this._getOptionalColumnsStorageKeyParts(),
            callback: function (res) {
                storedOptionalColumns = res;
            },
        });
        _.each(this.arch.children, function (c) {
            if (c.tag !== 'control' && c.tag !== 'groupby' && c.tag !== 'header') {
                var reject = c.attrs.modifiers.column_invisible;
                // If there is an evaluated domain for the field we override the node
                // attribute to have the evaluated modifier value.
                if (c.tag === "button_group") {
                    // FIXME: 'column_invisible' attribute is available for fields *and* buttons,
                    // so 'columnInvisibleFields' variable name is misleading, it should be renamed
                    reject = c.children.every(child => columnInvisibleFields[child.attrs.name]);
                } else if (c.attrs.name in columnInvisibleFields) {
                    reject = columnInvisibleFields[c.attrs.name];
                }
                if (!reject && c.attrs.widget === 'handle') {
                    self.handleField = c.attrs.name;
                    if (self.isGrouped) {
                        reject = true;
                    }
                }

                if (!reject && c.attrs.optional) {
                    self.optionalColumns.push(c);
                    var enabled;
                    if (storedOptionalColumns === undefined) {
                        enabled = c.attrs.optional === 'show';
                    } else {
                        enabled = _.contains(storedOptionalColumns, c.attrs.name);
                    }
                    if (enabled) {
                        self.optionalColumnsEnabled.push(c.attrs.name);
                    }
                    reject = !enabled;
                }

                if (!reject) {
                    self.columns.push(c);
                }
            }
        });
    },
    /**
     * Classnames "oe_edit_only" and "oe_read_only" aim to only display the cell
     * in the corresponding mode. This only concerns lists inside form views
     * (for x2many fields). This function detects the className and stores a
     * flag on the node's attrs accordingly, to ease further computations.
     *
     * @private
     */
    _processModeClassNames: function () {
        this.arch.children.forEach(c => {
            if (c.attrs.class) {
                c.attrs.editOnly = /\boe_edit_only\b/.test(c.attrs.class);
                c.attrs.readOnly = /\boe_read_only\b/.test(c.attrs.class);
            }
        });
    },
    /**
     * Render a list of <td>, with aggregates if available.  It can be displayed
     * in the footer, or for each open groups.
     *
     * @private
     * @param {any} aggregateValues
     * @returns {jQueryElement[]} a list of <td> with the aggregate values
     */
    _renderAggregateCells: function (aggregateValues) {
        var self = this;

        return _.map(this.columns, function (column) {
            var $cell = $('<td>');
            if (config.isDebug()) {
                $cell.addClass(column.attrs.name);
            }
            if (column.attrs.editOnly) {
                $cell.addClass('oe_edit_only');
            }
            if (column.attrs.readOnly) {
                $cell.addClass('oe_read_only');
            }
            if (column.attrs.name in aggregateValues) {
                var field = self.state.fields[column.attrs.name];
                var value = aggregateValues[column.attrs.name].value;
                var help = aggregateValues[column.attrs.name].help;
                var formatFunc = field_utils.format[column.attrs.widget];
                if (!formatFunc) {
                    formatFunc = field_utils.format[field.type];
                }
                var formattedValue = formatFunc(value, field, {
                    escape: true,
                    digits: column.attrs.digits ? JSON.parse(column.attrs.digits) : undefined,
                });
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
     * @private
     * @returns {jQueryElement} a jquery element <tbody>
     */
    _renderBody: function () {
        var self = this;
        var $rows = this._renderRows();
        while ($rows.length < 4) {
            $rows.push(self._renderEmptyRow());
        }
        return $('<tbody>').append($rows);
    },
    /**
     * Render a cell for the table. For most cells, we only want to display the
     * formatted value, with some appropriate css class. However, when the
     * node was explicitely defined with a 'widget' attribute, then we
     * instantiate the corresponding widget.
     *
     * @private
     * @param {Object} record
     * @param {Object} node
     * @param {integer} colIndex
     * @param {Object} [options]
     * @param {Object} [options.mode]
     * @param {Object} [options.renderInvisible=false]
     *        force the rendering of invisible cell content
     * @param {Object} [options.renderWidgets=false]
     *        force the rendering of the cell value thanks to a widget
     * @returns {jQueryElement} a <td> element
     */
    _renderBodyCell: function (record, node, colIndex, options) {
        var tdClassName = 'o_data_cell';
        if (node.tag === 'button_group') {
            tdClassName += ' o_list_button';
        } else if (node.tag === 'field') {
            tdClassName += ' o_field_cell';
            var typeClass = FIELD_CLASSES[this.state.fields[node.attrs.name].type];
            if (typeClass) {
                tdClassName += (' ' + typeClass);
            }
            if (node.attrs.widget) {
                tdClassName += (' o_' + node.attrs.widget + '_cell');
            }
        }
        if (node.attrs.editOnly) {
            tdClassName += ' oe_edit_only';
        }
        if (node.attrs.readOnly) {
            tdClassName += ' oe_read_only';
        }
        var $td = $('<td>', { class: tdClassName, tabindex: -1 });

        // We register modifiers on the <td> element so that it gets the correct
        // modifiers classes (for styling)
        var modifiers = this._registerModifiers(node, record, $td, _.pick(options, 'mode'));
        // If the invisible modifiers is true, the <td> element is left empty.
        // Indeed, if the modifiers was to change the whole cell would be
        // rerendered anyway.
        if (modifiers.invisible && !(options && options.renderInvisible)) {
            return $td;
        }

        if (node.tag === 'button_group') {
            for (const buttonNode of node.children) {
                if (!this.columnInvisibleFields[buttonNode.attrs.name]) {
                    $td.append(this._renderButton(record, buttonNode));
                }
            }
            return $td;
        } else if (node.tag === 'widget') {
            return $td.append(this._renderWidget(record, node));
        }
        if (node.attrs.widget || (options && options.renderWidgets)) {
            var $el = this._renderFieldWidget(node, record, _.pick(options, 'mode'));
            return $td.append($el);
        }
        this._handleAttributes($td, node);
        this._setDecorationClasses($td, this.fieldDecorations[node.attrs.name], record);

        var name = node.attrs.name;
        var field = this.state.fields[name];
        var value = record.data[name];
        var formatter = field_utils.format[field.type];
        var formatOptions = {
            escape: true,
            data: record.data,
            isPassword: 'password' in node.attrs,
            digits: node.attrs.digits && JSON.parse(node.attrs.digits),
        };
        var formattedValue = formatter(value, field, formatOptions);
        var title = '';
        if (field.type !== 'boolean') {
            title = formatter(value, field, _.extend(formatOptions, {escape: false}));
        }
        return $td.html(formattedValue).attr('title', title).attr('name', name);
    },
    /**
     * Renders the button element associated to the given node and record.
     *
     * @private
     * @param {Object} record
     * @param {Object} node
     * @returns {jQuery} a <button> element
     */
    _renderButton: function (record, node) {
        var self = this;
        var nodeWithoutWidth = Object.assign({}, node);
        delete nodeWithoutWidth.attrs.width;

        let extraClass = '';
        if (node.attrs.icon) {
            // if there is an icon, we force the btn-link style, unless a btn-xxx
            // style class is explicitely provided
            const btnStyleRegex = /\bbtn-[a-z]+\b/;
            if (!btnStyleRegex.test(nodeWithoutWidth.attrs.class)) {
                extraClass = 'btn-link o_icon_button';
            }
        }
        var $button = viewUtils.renderButtonFromNode(nodeWithoutWidth, {
            extraClass: extraClass,
        });
        this._handleAttributes($button, node);
        this._registerModifiers(node, record, $button);

        if (record.res_id) {
            // TODO this should be moved to a handler
            const debouncedClick = _.debounce(() => {
                self.trigger_up('button_clicked', {
                    attrs: node.attrs,
                    record: record,
                });
            }, 500, true);
            $button.on("click", (e) => {
                e.stopPropagation();
                debouncedClick();
            });
        } else {
            if (node.attrs.options.warn) {
                $button.on("click", function (e) {
                    e.stopPropagation();
                    self.displayNotification({ message: _t('Please click on the "save" button first'), type: 'danger' });
                });
            } else {
                $button.prop('disabled', true);
            }
        }

        return $button;
    },
    /**
     * Render a complete empty row.  This is used to fill in the blanks when we
     * have less than 4 lines to display.
     *
     * @private
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
     * @private
     * @returns {jQueryElement} a <tfoot> element
     */
    _renderFooter: function () {
        var aggregates = {};
        _.each(this.columns, function (column) {
            if ('aggregate' in column) {
                aggregates[column.attrs.name] = column.aggregate;
            }
        });
        var $cells = this._renderAggregateCells(aggregates);
        if (this.hasSelectors) {
            $cells.unshift($('<td>'));
        }
        return $('<tfoot>').append($('<tr>').append($cells));
    },
    /**
     * Renders the group button element.
     *
     * @private
     * @param {Object} record
     * @param {Object} group
     * @returns {jQuery} a <button> element
     */
    _renderGroupButton: function (list, node) {
        var $button = viewUtils.renderButtonFromNode(node, {
            extraClass: node.attrs.icon ? 'o_icon_button' : undefined,
            textAsTitle: !!node.attrs.icon,
        });
        this._handleAttributes($button, node);
        this._registerModifiers(node, list.groupData, $button);

        // TODO this should be moved to event handlers
        $button.on("click", this._onGroupButtonClicked.bind(this, list.groupData, node));
        $button.on("keydown", this._onGroupButtonKeydown.bind(this));

        return $button;
    },
    /**
     * Renders the group buttons.
     *
     * @private
     * @param {Object} record
     * @param {Object} group
     * @returns {jQuery} a <button> element
     */
    _renderGroupButtons: function (list, group) {
        var self = this;
        var $buttons = $();
        if (list.value) {
            // buttons make no sense for 'Undefined' group
            group.arch.children.forEach(function (child) {
                if (child.tag === 'button') {
                    $buttons = $buttons.add(self._renderGroupButton(list, child));
                }
            });
        }
        return $buttons;
    },
    /**
     * Render the row that represent a group
     *
     * @private
     * @param {Object} group
     * @param {integer} groupLevel the nesting level (0 for root groups)
     * @returns {jQueryElement} a <tr> element
     */
    _renderGroupRow: function (group, groupLevel) {
        var cells = [];

        const groupBy = this.state.groupedBy[groupLevel];
        const groupByFieldName = groupBy.split(':')[0];
        const groupByField = group.fields[groupByFieldName];
        const name = groupByField.type === "boolean"
            ? (group.value === undefined ? _t('None') : (group.value ? _t('Yes') : _t('No')))
            : (group.value === undefined || group.value === false ? _t('None') : group.value);
        var $th = $('<th>')
            .addClass('o_group_name')
            .attr('tabindex', -1)
            .text(name + ' (' + group.count + ')');
        var $arrow = $('<span>')
            .css('padding-left', 2 + (groupLevel * 20) + 'px')
            .css('padding-right', '5px')
            .addClass('fa');
        if (group.count > 0) {
            $arrow.toggleClass('fa-caret-right', !group.isOpen)
                .toggleClass('fa-caret-down', group.isOpen);
        }
        $th.prepend($arrow);
        cells.push($th);

        var aggregateKeys = Object.keys(group.aggregateValues);
        var aggregateValues = _.mapObject(group.aggregateValues, function (value) {
            return { value: value };
        });
        var aggregateCells = this._renderAggregateCells(aggregateValues);
        var firstAggregateIndex = _.findIndex(this.columns, function (column) {
            return column.tag === 'field' && _.contains(aggregateKeys, column.attrs.name);
        });
        var colspanBeforeAggregate;
        if (firstAggregateIndex !== -1) {
            // if there are aggregates, the first $th goes until the first
            // aggregate then all cells between aggregates are rendered
            colspanBeforeAggregate = firstAggregateIndex;
            var lastAggregateIndex = _.findLastIndex(this.columns, function (column) {
                return column.tag === 'field' && _.contains(aggregateKeys, column.attrs.name);
            });
            cells = cells.concat(aggregateCells.slice(firstAggregateIndex, lastAggregateIndex + 1));
            var colSpan = this.columns.length - 1 - lastAggregateIndex;
            if (colSpan > 0) {
                cells.push($('<th>').attr('colspan', colSpan));
            }
        } else {
            var colN = this.columns.length;
            colspanBeforeAggregate = colN > 1 ? colN - 1 : 1;
            if (colN > 1) {
                cells.push($('<th>'));
            }
        }
        if (this.hasSelectors) {
            colspanBeforeAggregate += 1;
        }
        $th.attr('colspan', colspanBeforeAggregate);

        if (group.isOpen && !group.groupedBy.length && (group.count > group.data.length)) {
            const lastCell = cells[cells.length - 1][0];
            this._renderGroupPager(group, lastCell);
        }
        if (group.isOpen && this.groupbys[groupBy]) {
            var $buttons = this._renderGroupButtons(group, this.groupbys[groupBy]);
            if ($buttons.length) {
                var $buttonSection = $('<div>', {
                    class: 'o_group_buttons',
                }).append($buttons);
                $th.append($buttonSection);
            }
        }
        return $('<tr>')
            .addClass('o_group_header')
            .toggleClass('o_group_open', group.isOpen)
            .toggleClass('o_group_has_content', group.count > 0)
            .data('group', group)
            .append(cells);
    },
    /**
     * Render the content of a given opened group.
     *
     * @private
     * @param {Object} group
     * @param {integer} groupLevel the nesting level (0 for root groups)
     * @returns {jQueryElement} a <tr> element
     */
    _renderGroup: function (group, groupLevel) {
        var self = this;
        if (group.groupedBy.length) {
            // the opened group contains subgroups
            return this._renderGroups(group.data, groupLevel + 1);
        } else {
            // the opened group contains records
            var $records = _.map(group.data, function (record) {
                return self._renderRow(record);
            });
            return [$('<tbody>').append($records)];
        }
    },
    /**
     * Renders the pager for a given group
     *
     * @private
     * @param {Object} group
     * @param {HTMLElement} target
     */
    _renderGroupPager: function (group, target) {
        const currentMinimum = group.offset + 1;
        const limit = group.limit;
        const size = group.count;
        if (!this._shouldRenderPager(currentMinimum, limit, size)) {
            return;
        }
        const pager = new ComponentWrapper(this, Pager, {
            currentMinimum,
            limit,
            size,
            onPagerChanged: this._onPagerChanged.bind(this, group),
        });
        const pagerMounting = pager.mount(target).then(() => {
            // Prevent pager clicks to toggle the group.
            pager.el.addEventListener('click', ev => ev.stopPropagation());
        });
        this.defs.push(pagerMounting);
        this.pagers.push(pager);
    },
    /**
     * Render all groups in the view.  We assume that the view is in grouped
     * mode.
     *
     * Note that each group is rendered inside a <tbody>, which contains a group
     * row, then possibly a bunch of rows for each record.
     *
     * @private
     * @param {Object} data the dataPoint containing the groups
     * @param {integer} [groupLevel=0] the nesting level. 0 is for the root group
     * @returns {jQueryElement[]} a list of <tbody>
     */
    _renderGroups: function (data, groupLevel) {
        var self = this;
        groupLevel = groupLevel || 0;
        var result = [];
        var $tbody = $('<tbody>');
        _.each(data, function (group) {
            if (!$tbody) {
                $tbody = $('<tbody>');
            }
            $tbody.append(self._renderGroupRow(group, groupLevel));
            if (group.data.length) {
                result.push($tbody);
                result = result.concat(self._renderGroup(group, groupLevel));
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
     * @private
     * @returns {jQueryElement} a <thead> element
     */
    _renderHeader: function () {
        var $tr = $('<tr>')
            .append(_.map(this.columns, this._renderHeaderCell.bind(this)));
        if (this.hasSelectors) {
            $tr.prepend(this._renderSelector('th'));
        }
        return $('<thead>').append($tr);
    },
    /**
     * Render a single <th> with the informations for a column. If it is not a
     * field or nolabel attribute is set to "1", the th will be empty.
     * Otherwise, it will contains all relevant information for the field.
     *
     * @private
     * @param {Object} node
     * @returns {jQueryElement} a <th> element
     */
    _renderHeaderCell: function (node) {
        const { icon, name, string } = node.attrs;
        var order = this.state.orderedBy;
        var isNodeSorted = order[0] && order[0].name === name;
        var field = this.state.fields[name];
        var $th = $('<th>');
        if (name) {
            $th.attr('data-name', name);
        } else if (string) {
            $th.attr('data-string', string);
        } else if (icon) {
            $th.attr('data-icon', icon);
        }
        if (node.attrs.editOnly) {
            $th.addClass('oe_edit_only');
        }
        if (node.attrs.readOnly) {
            $th.addClass('oe_read_only');
        }
        if (node.tag === 'button_group') {
            $th.addClass('o_list_button');
        }
        if (!field || node.attrs.nolabel === '1') {
            return $th;
        }
        var description = string || field.string;
        if (node.attrs.widget) {
            $th.addClass(' o_' + node.attrs.widget + '_cell');
            const FieldWidget = this.state.fieldsInfo.list[name].Widget;
            if (FieldWidget.prototype.noLabel) {
                description = '';
            } else if (FieldWidget.prototype.label) {
                description = FieldWidget.prototype.label;
            }
        }
        $th.text(description)
            .attr('tabindex', -1)
            .toggleClass('o-sort-down', isNodeSorted ? !order[0].asc : false)
            .toggleClass('o-sort-up', isNodeSorted ? order[0].asc : false)
            .addClass((field.sortable || this.state.fieldsInfo.list[name].options.allow_order || false) && 'o_column_sortable');

        if (isNodeSorted) {
            $th.attr('aria-sort', order[0].asc ? 'ascending' : 'descending');
        }

        if (field.type === 'float' || field.type === 'integer' || field.type === 'monetary') {
            $th.addClass('o_list_number_th');
        }

        if (config.isDebug()) {
            var fieldDescr = {
                field: field,
                name: name,
                string: description || name,
                record: this.state,
                attrs: _.extend({}, node.attrs, this.state.fieldsInfo.list[name]),
            };
            this._addFieldTooltip(fieldDescr, $th);
        } else {
            $th.attr('title', description);
        }
        return $th;
    },
    /**
     * Render a row, corresponding to a record.
     *
     * @private
     * @param {Object} record
     * @returns {jQueryElement} a <tr> element
     */
    _renderRow: function (record) {
        var self = this;
        var $cells = this.columns.map(function (node, index) {
            return self._renderBodyCell(record, node, index, { mode: 'readonly' });
        });

        var $tr = $('<tr/>', { class: 'o_data_row' })
            .attr('data-id', record.id)
            .append($cells);
        if (this.hasSelectors) {
            $tr.prepend(this._renderSelector('td', !record.res_id));
        }
        if (this.no_open && this.mode === "readonly") {
            $tr.addClass('o_list_no_open');
        }
        this._setDecorationClasses($tr, this.rowDecorations, record);
        return $tr;
    },
    /**
     * Render all rows. This method should only called when the view is not
     * grouped.
     *
     * @private
     * @returns {jQueryElement[]} a list of <tr>
     */
    _renderRows: function () {
        return this.state.data.map(this._renderRow.bind(this));
    },
    /**
     * Render a single <th> with dropdown menu to display optional columns of view.
     *
     * @private
     * @returns {jQueryElement} a <th> element
     */
    _renderOptionalColumnsDropdown: function () {
        var self = this;
        var $optionalColumnsDropdown = $('<div>', {
            class: 'o_optional_columns text-center dropdown',
        });
        var $a = $("<a>", {
            'class': "dropdown-toggle text-dark o-no-caret",
            'href': "#",
            'role': "button",
            'data-bs-toggle': "dropdown",
            'data-bs-offset': "0,30",
            'aria-expanded': false,
            'aria-label': _t('Optional columns'),
        });
        $a.appendTo($optionalColumnsDropdown);

        // Set the expansion direction of the dropdown
        // The button is located at the end of the list headers
        // We want the dropdown to expand towards the list rather than away from it
        // https://getbootstrap.com/docs/4.0/components/dropdowns/#menu-alignment
        var direction = _t.database.parameters.direction;
        var dropdownMenuClass = direction === 'rtl' ? 'dropdown-menu-start' : 'dropdown-menu-end';
        var $dropdown = $("<div>", {
            class: 'dropdown-menu o_optional_columns_dropdown ' + dropdownMenuClass,
            role: 'menu',
        });
        this.optionalColumns.forEach(function (col) {
            var txt = (col.attrs.string || self.state.fields[col.attrs.name].string) +
                (config.isDebug() ? (' (' + col.attrs.name + ')') : '');
            var $checkbox = dom.renderCheckbox({
                text: txt,
                role: "menuitemcheckbox",
                prop: {
                    name: col.attrs.name,
                    checked: _.contains(self.optionalColumnsEnabled, col.attrs.name),
                }
            });
            $dropdown.append($("<div>", {
                class: "dropdown-item",
            }).append($checkbox));
        });
        $dropdown.appendTo($optionalColumnsDropdown);
        return $optionalColumnsDropdown;
    },
    /**
     * A 'selector' is the small checkbox on the left of a record in a list
     * view.  This is rendered as an input inside a div, so we can properly
     * style it.
     *
     * Note that it takes a tag in argument, because selectors in the header
     * are renderd in a th, and those in the tbody are in a td.
     *
     * @private
     * @param {string} tag either th or td
     * @param {boolean} disableInput if true, the input generated will be disabled
     * @returns {jQueryElement}
     */
    _renderSelector: function (tag, disableInput) {
        var $content = dom.renderCheckbox();
        if (disableInput) {
            $content.find("input[type='checkbox']").prop('disabled', disableInput);
        }
        return $('<' + tag + '>')
            .addClass('o_list_record_selector')
            .append($content);
    },
    /**
     * Main render function for the list.  It is rendered as a table. For now,
     * this method does not wait for the field widgets to be ready.
     *
     * @override
     * @returns {Promise} resolved when the view has been rendered
     */
    async _renderView() {
        const oldPagers = this.pagers;
        let prom;
        let tableWrapper;
        if (this.state.count > 0 || !this.noContentHelp) {
            // render a table if there are records, or if there is no no content
            // helper (empty table in this case)
            this.pagers = [];

            const orderedBy = this.state.orderedBy;
            this.hasHandle = orderedBy.length === 0 || orderedBy[0].name === this.handleField;
            this._computeAggregates();

            const $table = $(
                '<table class="o_list_table table table-sm table-hover table-striped"/>'
            );
            $table.toggleClass('o_list_table_grouped', this.isGrouped);
            $table.toggleClass('o_list_table_ungrouped', !this.isGrouped);
            const defs = [];
            this.defs = defs;
            if (this.isGrouped) {
                $table.append(this._renderHeader());
                $table.append(this._renderGroups(this.state.data));
                $table.append(this._renderFooter());

            } else {
                $table.append(this._renderHeader());
                $table.append(this._renderBody());
                $table.append(this._renderFooter());
            }
            tableWrapper = Object.assign(document.createElement('div'), {
                className: 'table-responsive',
            });
            tableWrapper.appendChild($table[0]);
            delete this.defs;
            prom = Promise.all(defs);
        }

        await Promise.all([this._super.apply(this, arguments), prom]);

        this.el.innerHTML = "";
        this.el.classList.remove('o_list_optional_columns');

        // destroy the previously instantiated pagers, if any
        oldPagers.forEach(pager => pager.destroy());

        // append the table (if any) to the main element
        if (tableWrapper) {
            this.el.appendChild(tableWrapper);
            if (document.body.contains(this.el)) {
                this.pagers.forEach(pager => pager.on_attach_callback());
            }
            if (this._shouldRenderOptionalColumnsDropdown()) {
                this.el.classList.add('o_list_optional_columns');
                this.$('table').append(
                    $('<i class="o_optional_columns_dropdown_toggle oi oi-fw oi-settings-adjust lh-base"/>')
                );
                this.$el.append(this._renderOptionalColumnsDropdown());
            }
            if (this.selection.length) {
                const $checked_rows = this.$('tr').filter(
                    (i, el) => this.selection.includes(el.dataset.id)
                );
                $checked_rows.find('.o_list_record_selector input').prop('checked', true);
                if ($checked_rows.length === this.$('.o_data_row').length) { // all rows are checked
                    this.$('thead .o_list_record_selector input').prop('checked', true);
                }
            }
        }

        // display the no content helper if necessary
        if (!this._hasContent() && !!this.noContentHelp) {
            this._renderNoContentHelper();
        }
    },
    /**
     * Each line or cell can be decorated according to a few simple rules. The
     * arch description of the list or the field nodes may have one of the
     * decoration-X attributes with a python expression as value. Then, for each
     * record, we evaluate the python expression, and conditionnaly add the
     * text-X css class to the element.  This method is concerned with the
     * computation of the list of css classes for a given record.
     *
     * @private
     * @param {jQueryElement} $el the element to which to add the classes (a tr
     *   or td)
     * @param {Object} decorations keys are the decoration classes (e.g.
     *   'fw-bold') and values are the python expressions to evaluate
     * @param {Object} record a basic model record
     */
    _setDecorationClasses: function ($el, decorations, record) {
        for (const [cssClass, expr] of Object.entries(decorations)) {
            $el.toggleClass(cssClass, py.PY_isTrue(py.evaluate(expr, record.evalContext)));
        }
    },
    /**
     * @private
     * @returns {boolean}
     */
    _shouldRenderPager: function (currentMinimum, limit, size) {
        if (!limit || !size) {
            return false;
        }
        const maximum = Math.min(currentMinimum + limit - 1, size);
        const singlePage = (1 === currentMinimum) && (maximum === size);
        return !singlePage;
    },
    /**
     * @private
     * @returns {boolean}
     */
    _shouldRenderOptionalColumnsDropdown: function () {
        return this.optionalColumns.length;
    },
    /**
     * Update the footer aggregate values.  This method should be called each
     * time the state of some field is changed, to make sure their sum are kept
     * in sync.
     *
     * @private
     */
    _updateFooter: function () {
        this._computeAggregates();
        this.$('tfoot').replaceWith(this._renderFooter());
    },
    /**
     * Whenever we change the state of the selected rows, we need to call this
     * method to keep the this.selection variable in sync, and also to recompute
     * the aggregates.
     *
     * @private
     */
    _updateSelection: function () {
        const previousSelection = JSON.stringify(this.selection);
        this.selection = [];
        var self = this;
        var $inputs = this._getSelectableRecordCheckboxes();
        var allChecked = $inputs.length > 0;
        $inputs.each(function (index, input) {
            if (input.checked) {
                self.selection.push($(input).closest('tr').data('id'));
            } else {
                allChecked = false;
            }
        });
        this.$('thead .o_list_record_selector input').prop('checked', allChecked);
        if (JSON.stringify(this.selection) !== previousSelection) {
            this.trigger_up('selection_changed', { allChecked, selection: this.selection });
        }
        this._updateFooter();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} record a record dataPoint on which the button applies
     * @param {Object} node arch node of the button
     * @param {Object} node.attrs the attrs of the button in the arch
     * @param {jQueryEvent} ev
     */
    _onGroupButtonClicked: function (record, node, ev) {
        ev.stopPropagation();
        if (node.attrs.type === 'edit') {
            this.trigger_up('group_edit_button_clicked', {
                record: record,
            });
        } else {
            this.trigger_up('button_clicked', {
                attrs: node.attrs,
                record: record,
            });
        }
    },
    /**
     * If the user presses ENTER on a group header button, we want to execute
     * the button action. This is done automatically as the click handler is
     * called. However, we have to stop the propagation of the event to prevent
     * another handler from closing the group (see _onKeyDown).
     *
     * @private
     * @param {jQueryEvent} ev
     */
    _onGroupButtonKeydown: function (ev) {
        if (ev.keyCode === $.ui.keyCode.ENTER) {
            ev.stopPropagation();
        }
    },
    /**
     * When the user clicks on the checkbox in optional fields dropdown the
     * column is added to listview and displayed
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onToggleOptionalColumn: function (ev) {
        var self = this;
        ev.stopPropagation();
        // when the input's label is clicked, the click event is also raised on the
        // input itself (https://developer.mozilla.org/en-US/docs/Web/HTML/Element/label),
        // so this handler is executed twice (except if the rendering is quick enough,
        // as when we render, we empty the HTML)
        ev.preventDefault();
        var input = ev.currentTarget.querySelector('input');
        var fieldIndex = this.optionalColumnsEnabled.indexOf(input.name);
        if (fieldIndex >= 0) {
            this.optionalColumnsEnabled.splice(fieldIndex, 1);
        } else {
            this.optionalColumnsEnabled.push(input.name);
        }
        this.trigger_up('save_optional_fields', {
            keyParts: this._getOptionalColumnsStorageKeyParts(),
            optionalColumnsEnabled: this.optionalColumnsEnabled,
        });
        this._processColumns(this.columnInvisibleFields);
        this._render().then(function () {
            self._onToggleOptionalColumnDropdown(ev);
        });
    },
    /**
     * When the user clicks on the three dots (ellipsis), toggle the optional
     * fields dropdown.
     *
     * @private
     */
    _onToggleOptionalColumnDropdown: function (ev) {
        // The dropdown toggle is inside the overflow hidden container because
        // the ellipsis is always in the last column, but we want the actual
        // dropdown to be outside of the overflow hidden container since it
        // could easily have a higher height than the table. However, separating
        // the toggle and the dropdown itself is not supported by popper.js by
        // default, which is why we need to toggle the dropdown manually.
        ev.stopPropagation();
        this.$('.o_optional_columns .dropdown-toggle').dropdown('toggle');
        // Explicitly set left/right of the optional column dropdown as it is pushed
        // inside this.$el, so we need to position it at the end of top left corner.
        var position = (this.$(".table-responsive").css('overflow') === "auto" ? this.$el.width() :
            this.$('table').width());
        var direction = "left";
        if (_t.database.parameters.direction === 'rtl') {
            position = position - this.$('.o_optional_columns .o_optional_columns_dropdown').width();
            direction = "right";
        }
        this.$('.o_optional_columns').css(direction, position);
    },
    /**
     * Manages the keyboard events on the list. If the list is not editable, when the user navigates to
     * a cell using the keyboard, if he presses enter, enter the model represented by the line
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeyDown: function (ev) {
        var $cell = $(ev.currentTarget);
        var $tr;
        var $futureCell;
        var colIndex;
        if (this.state.isSample) {
            return; // we disable keyboard navigation inside the table in "sample" mode
        }
        switch (ev.keyCode) {
            case $.ui.keyCode.LEFT:
                ev.preventDefault();
                $tr = $cell.closest('tr');
                $tr.closest('tbody').addClass('o_keyboard_navigation');
                if ($tr.hasClass('o_group_header') && $tr.hasClass('o_group_open')) {
                    this._onToggleGroup(ev);
                } else {
                    $futureCell = $cell.prev();
                }
                break;
            case $.ui.keyCode.RIGHT:
                ev.preventDefault();
                $tr = $cell.closest('tr');
                $tr.closest('tbody').addClass('o_keyboard_navigation');
                if ($tr.hasClass('o_group_header') && !$tr.hasClass('o_group_open')) {
                    this._onToggleGroup(ev);
                } else {
                    $futureCell = $cell.next();
                }
                break;
            case $.ui.keyCode.UP:
                ev.preventDefault();
                $cell.closest('tbody').addClass('o_keyboard_navigation');
                colIndex = this.currentColIndex || $cell.index();
                $futureCell = this._findConnectedCell($cell, 'prev', colIndex);
                if (!$futureCell) {
                    this.trigger_up('navigation_move', { direction: 'up' });
                }
                break;
            case $.ui.keyCode.DOWN:
                ev.preventDefault();
                $cell.closest('tbody').addClass('o_keyboard_navigation');
                colIndex = this.currentColIndex || $cell.index();
                $futureCell = this._findConnectedCell($cell, 'next', colIndex);
                break;
            case $.ui.keyCode.ENTER:
                ev.preventDefault();
                $tr = $cell.closest('tr');
                if ($tr.hasClass('o_group_header')) {
                    this._onToggleGroup(ev);
                } else {
                    var id = $tr.data('id');
                    if (id) {
                        this.trigger_up('open_record', { id: id, target: ev.target });
                    }
                }
                break;
        }
        if ($futureCell) {
            // If the cell contains activable elements, focus them instead (except if it is in a
            // group header, in which case we want to activate the whole header, so that we can
            // open/close it with RIGHT/LEFT keystrokes)
            var isInGroupHeader = $futureCell.closest('tr').hasClass('o_group_header');
            var $activables = !isInGroupHeader && $futureCell.find(':focusable');
            if ($activables.length) {
                $activables[0].focus();
            } else {
                $futureCell.focus();
            }
        }
    },
    /**
     * @private
     */
    _onMouseDown: function () {
        $('.o_keyboard_navigation').removeClass('o_keyboard_navigation');
    },
    /**
     * @private
     * @param {OwlEvent} ev
     * @param {Object} group
     */
    _onPagerChanged: async function (group, { currentMinimum, limit }) {
        this.trigger_up('load', {
            id: group.id,
            limit: limit,
            offset: currentMinimum - 1,
            on_success: reloadedGroup => {
                Object.assign(group, reloadedGroup);
                this._render();
            },
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onRowClicked: function (ev) {
        // The special_click property explicitely allow events to bubble all
        // the way up to bootstrap's level rather than being stopped earlier.
        if (!ev.target.closest('.o_list_record_selector') && !$(ev.target).prop('special_click') && !this.no_open) {
            var id = $(ev.currentTarget).data('id');
            if (id) {
                this.trigger_up('open_record', { id: id, target: ev.target });
            }
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onSelectRecord: function (ev) {
        ev.stopPropagation();
        this._updateSelection();
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onSortColumn: function (ev) {
        var name = $(ev.currentTarget).data('name');
        this.trigger_up('toggle_column_order', { id: this.state.id, name: name });
    },
    /**
     * When the user clicks on the whole record selector cell, we want to toggle
     * the checkbox, to make record selection smooth.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onToggleCheckbox: function (ev) {
        const $recordSelector = $(ev.target).find('input[type=checkbox]:not(":disabled")');
        $recordSelector.prop('checked', !$recordSelector.prop("checked"));
        $recordSelector.change(); // s.t. th and td checkbox cases are handled by their own handler
    },
    /**
     * @private
     * @param {DOMEvent} ev
     */
    _onToggleGroup: function (ev) {
        ev.preventDefault();
        var group = $(ev.currentTarget).closest('tr').data('group');
        if (group.count) {
            this.trigger_up('toggle_group', {
                group: group,
                onSuccess: () => {
                    this._updateSelection();
                    // Refocus the header after re-render unless the user
                    // already focused something else by now
                    if (document.activeElement.tagName === 'BODY') {
                        var groupHeaders = $('tr.o_group_header:data("group")');
                        var header = groupHeaders.filter(function () {
                            return $(this).data('group').id === group.id;
                        });
                        header.find('.o_group_name').focus();
                    }
                },
            });
        }
    },
    /**
     * When the user clicks on the row selection checkbox in the header, we
     * need to update the checkbox of the row selection checkboxes in the body.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onToggleSelection: function (ev) {
        var checked = $(ev.currentTarget).prop('checked') || false;
        this.$('tbody .o_list_record_selector input:not(":disabled")').prop('checked', checked);
        this._updateSelection();
    },
});

export default ListRenderer;
