odoo.define('web.EditableListRenderer', function (require) {
"use strict";

/**
 * Editable List renderer
 *
 * The list renderer is reasonably complex, so we split it in two files.  This
 * file simply 'includes' the basic ListRenderer to add all the necessary
 * behavior to enable editing records.
 *
 * Unlike Odoo v10 and before, this list renderer is independant from the form
 * view.  It uses the same widgets, but the code is totally stand alone.
 */

var core = require('web.core');
var Domain = require('web.Domain');
var ListRenderer = require('web.ListRenderer');

var _t = core._t;

ListRenderer.include({
    custom_events: {
        field_changed: '_onFieldChanged',
        move_down: '_onMoveDown',
        move_up: '_onMoveUp',
        move_left: '_onMoveLeft',
        move_right: '_onMoveRight',
        move_next: '_onMoveNext',
        move_next_line: '_onMoveNextLine',
    },
    events: _.extend({}, ListRenderer.prototype.events, {
        'click tbody td': '_onCellClick',
        'click tbody tr:not(.o_data_row)': '_onEmptyRowClick',
        'click tfoot': '_onFooterClick',
        'click tr .o_list_record_delete': '_onTrashIconClick',
        'click .o_form_field_x2many_list_row_add a': '_onAddRecord',
    }),
    /**
     * @override
     * @param {Object} params
     * @param {string} params.mode either 'readonly' or 'edit'
     * @param {boolean} params.addCreateLine
     * @param {boolean} params.addTrashIcon
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);

        this.mode = params.mode;

        // if addCreateLine is true, the renderer will add a 'Add an item' link
        // at the bottom of the list view
        this.addCreateLine = params.addCreateLine;

        // if addTrashIcon is true, there will be a small trash icon at the end
        // of each line, so the user can delete a record.
        this.addTrashIcon = params.addTrashIcon;

        this.editable = this.arch.attrs.editable;

        this.currentRow = null;
        this.currentCol = null;
    },
    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        if (this.mode === 'edit') {
            this.$el.css({height: '100%'});
            core.bus.on('click', this, this._onWindowClicked.bind(this));
        }
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * This method is called by the controller, when a change has been confirmed
     * by the model.  In that situation, we need to properly update the cell
     * widgets.  (it is necessary, because the value could have been changed by
     * an onchange).
     *
     * Note that it could happen that the changedRecordID is not found in the
     * current state.  This is possible if a change in a record caused an
     * onchange which erased the current record.  In that case, we simply
     * rerender the list.
     *
     * @param {Object} state a record resource (the new full state)
     * @param {string} changedRecordID the local id for the changed record
     * @param {string[]} changedFields list of modified fields
     * @param {OdooEvent} event the event that triggered the change
     */
    confirmChange: function (state, changedRecordID, changedFields, event) {
        this.state = state;
        var rowIndex = _.findIndex(this.state.data, {id: changedRecordID});
        if (rowIndex > -1) {
            this._updateRow(rowIndex, changedFields, event);
        } else {
            this._render();
        }
    },
    /**
     * This method is called by the controller when the user has clicked 'save',
     * and the model as actually saved the current changes.  We then need to
     * set the correct values for each cell. The difference with confirmChange
     * is that the edited line is now in readonly mode, so we can just set its
     * new value.
     *
     * @param {Object} state the new full state for the list
     * @param {string} savedRecordID the id for the saved record
     */
    confirmSave: function (state, savedRecordID) {
        this.state = state;
        var index = _.findIndex(this.state.data, {id: savedRecordID});
        for (var j = 0; j < this.columns.length; j++) {
            this._setCellValue(index, j, false);
        }
    },
    /**
     * Edit a given record in the list
     *
     * @param {string} recordID
     */
    editRecord: function (recordID) {
        var index = _.findIndex(this.state.data, function (record) {
            return record.id === recordID;
        });
        this._selectCell(index, 0);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Find the td in a row corresponding the a field with a given index. The
     * main problem is that in some cases, we have a 'selector' checkbox, so the
     * correct td is sometimes at position i, sometimes at i+1
     *
     * @param {jQueryElement} $row the $tr for the row we are interested in
     * @param {number} index the index of the field/column
     * @returns {jQueryElement} the $td for the index-th field
     */
    _findTd: function ($row, index) {
        return $row.find('td').eq(index + (this.hasSelectors ? 1 : 0));
    },
    /**
     * Returns the current number of columns.  The editable renderer may add a
     * trash icon on the right of a record, so we need to take this into account
     *
     * @override
     * @returns {number}
     */
    _getNumberOfCols: function () {
        var n = this._super();
        if (this.addTrashIcon) {
            n++;
        }
        return n;
    },
    /**
     * Determine if a given cell is readonly.  A cell is considered readonly if
     * the field is readonly, or the widget is statically readonly (like the
     * sequence widget) of if there are a 'readonly' attr, with a matching
     * domain.
     *
     * @param {Object} record a basic model record
     * @param {Object} field a field description
     * @param {Object} node a node object (from the arch)
     * @returns {boolean}
     */
    _isReadonly: function (record, field, node) {
        if (field.readonly) {
            return true;
        }
        var Widget = this.state.fieldsInfo.list[node.attrs.name].Widget;
        if (Widget && Widget.prototype.readonly) {
            return true;
        }
        if ('readonly' in node.modifiers) {
            var fieldValues = this._getFieldValues(record);
            return new Domain(node.modifiers.readonly).compute(fieldValues);
        }
        return false;
    },
    /**
     * A cell is editable if its field isn't invisible and if it isn't readonly.
     *
     * @param {Object} record a basic model record
     * @param {Object} field a field description
     * @param {Object} node a node object (from the arch)
     * @returns {boolean}
     */
    _isEditable: function (record, field, node) {
        return !this._isInvisible(record, node) && !this._isReadonly(record, field, node);
    },
    /**
     * The renderer needs to support reordering lines.  This is only active in
     * edit mode. The hasHandle attribute is used when there is a sequence
     * widget.
     *
     * @override
     * @returns {jQueryElement}
     */
    _renderBody: function () {
        var $body = this._super();
        if (this.mode === 'edit' && this.hasHandle) {
            $body.sortable({
                axis: 'y',
                items: '> tr.o_data_row',
                helper: 'clone',
                handle: '.o_row_handle',
            });
        }
        return $body;
    },
    /**
     * Add all the necessary styling classes to displayed cells.  Also, we need
     * to add the current index to each cell data attribute, so we can get it
     * back when we need to select a cell.
     *
     * @override
     * @param {Object} record
     * @param {Object} node
     * @param {integer} index
     * @returns {jQueryElement}
     */
    _renderBodyCell: function (record, node, index) {
        if (this.mode === 'readonly') {
            return this._super.apply(this, arguments);
        }
        var $cell = this._super(record, node);
        if (node.tag === 'field') {
            var field = this.state.fields[node.attrs.name];
            if (field.required) {
                $cell.addClass('o_required_field');
            }
            if (this._isReadonly(record, field, node)) {
                $cell.addClass('o_readonly');
            }
        }
        return $cell.data('index', index);
    },
    /**
     * Helper method, to instantiate and render a field widget. It is only
     * called by _selectCell, when editing a row.  It kind of looks like the
     * _renderBodyCell method of ListRenderer, but it has to properly tag the
     * widget and to do other subtly different tasks, so it is awkward to try to
     * merge them.
     *
     * @private
     * @param {jQueryElement} $row
     * @param {Object} node
     * @param {integer} rowIndex
     * @param {integer} colIndex
     * @returns {AbstractField} the instance of the desired widget
     */
    _renderFieldWidget: function ($row, node, rowIndex, colIndex) {
        if (node.tag === 'button') {
            return;
        }
        var name = node.attrs.name;
        var record = this.state.data[rowIndex];
        var field = this.state.fields[name];
        if (!this._isEditable(record, field, node)) {
            return;
        }
        var $td = this._findTd($row, colIndex);
        var Widget = this.state.fieldsInfo.list[name].Widget;
        var widget = new Widget(this, name, record, {
            mode: 'edit',
            viewType: 'list',
        });
        if (widget.replace_element) {
            $td.empty();
        }
        $td.addClass('o_edit_mode');
        widget.appendTo($td);
        widget.__rowIndex = rowIndex;
        widget.__colIndex = colIndex;
        this.widgets.push(widget);
        return widget;
    },
    /**
     * Editable rows are extended with their index, and possibly a trash icon on
     * their right, to allow deleting the corresponding record.
     *
     * @override
     * @param {any} record
     * @param {any} index
     * @returns {jQueryElement}
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            $row.data('index', index);
        }
        if (this.addTrashIcon) {
            var $icon = $('<span>').addClass('fa fa-trash-o').attr('name', 'delete');
            var $td = $('<td>').addClass('o_list_record_delete').append($icon);
            $row.append($td);
        }
        return $row;
    },
    /**
     * If the editable list view has the parameter addCreateLine, we need to
     * add a last row with the necessary control.
     *
     * @override
     * @returns {jQueryElement}
     */
    _renderRows: function () {
        var $rows = this._super();
        if (this.addCreateLine) {
            var $a = $('<a href="#">').text(_t("Add an item"));
            var $td = $('<td>')
                        .attr('colspan', this._getNumberOfCols())
                        .addClass('o_form_field_x2many_list_row_add')
                        .append($a);
            var $tr = $('<tr>').append($td);
            $rows.push($tr);
        }
        return $rows;
    },
    /**
     * This is one of the trickiest method in the editable renderer.  It has to
     * do a lot of stuff: it has to determine which cell should be selected (if
     * the terget cell is readonly, we need to find another suitable cell), then
     * unselect the current row, and activate the line where the selected cell
     * is, if necessary.
     *
     * @param {integer} rowIndex
     * @param {integer} colIndex
     */
    _selectCell: function (rowIndex, colIndex) {
        var self = this;

        // do nothing if user tries to select current cell
        if (rowIndex === this.currentRow && colIndex === this.currentCol) {
            return;
        }

        // make sure the colIndex is on an editable field. otherwise, find
        // next editable field, or do nothing if no such field exists
        var data = this.state.data;
        var fields = this.state.fields;
        var col, field, isEditable, record;
        for (var i = 0; i < this.columns.length; i++) {
            col = this.columns[colIndex];
            record = data[rowIndex];
            field = fields[col.attrs.name];
            isEditable = this._isEditable(record, field, col);
            if (isEditable) {
                break;
            }
            colIndex = (colIndex + 1) % this.columns.length;
        }
        if (!isEditable) {
            return;
        }

        // if we are just changing active cell in the same row, activate the
        // corresponding widget and return
        if (rowIndex === this.currentRow) {
            var w = _.findWhere(this.widgets, {
                __rowIndex: rowIndex,
                __colIndex: colIndex
            });
            this.currentCol = colIndex;
            w.activate();
            return;
        }

        // if this is a different column, then we need to prepare for it by
        // unselecting the current row.  This will trigger the save.
        if (rowIndex !== this.currentRow) {
            this._unselectRow();
        }

        // instantiate column widgets
        var $row = this.$('tbody tr').eq(rowIndex);
        $row.addClass('o_selected_row');
        // force the width of each cell to its current value so that it won't
        // change if its content changes, to prevent the view from flickering
        $row.find('td').each(function () {
            var $td = $(this);
            $td.width($td.width());
        });

        _.each(this.columns, function (node, index) {
            var widget = self._renderFieldWidget($row, node, rowIndex, index);
            if (widget && index === colIndex) {
                widget.activate();
            }
        });

        this.currentRow = rowIndex;
        this.currentCol = colIndex;
        this.trigger_up('change_mode', {mode: 'edit'});
    },
    /**
     * Set the value of a cell.  This method can be called when the value of a
     * cell was modified, for example afte an onchange.
     *
     * @param {integer} rowIndex
     * @param {integer} colIndex
     * @param {boolean} keepDirtyFlag
     * @param {boolean} forceDirtyFlag
     */
    _setCellValue: function (rowIndex, colIndex, keepDirtyFlag, forceDirtyFlag) {
        var record = this.state.data[rowIndex];
        var node = this.columns[colIndex];
        var $td = this._findTd(this.$('tbody tr').eq(rowIndex), colIndex);
        var $new_td = this._renderBodyCell(record, node, colIndex);
        if (keepDirtyFlag && $td.hasClass('o_field_dirty') || forceDirtyFlag) {
            $new_td.addClass('o_field_dirty');
        }
        $td.replaceWith($new_td);
    },
    /**
     * Updates the row of a particular record of the editable list view.
     *
     * @param {index} index the index of the record whose row needs updating
     * @param {string[]} changed_fields names of the fields which changed
     * @param {OdooEvent} event the event that triggered the change
     */
    _updateRow: function (index, changed_fields, event) {
        var self = this;
        var record = this.state.data[index];
        _.each(changed_fields, function (field_name) {
            var widget = _.findWhere(self.widgets, {name: field_name});
            if (widget && widget.__rowIndex === index) {
                widget.reset(record, event);
                widget.$el.parent().addClass('o_field_dirty');
            } else {
                var column_index = _.findIndex(self.columns, function (column) {
                    return column.attrs.name === field_name;
                });
                self._setCellValue(index, column_index, true, true);
            }
        });
    },
    /**
     * This method is called whenever we click/move outside of a row that was
     * in edit mode. This is the moment we save all accumulated changes on that
     * row, if needed.
     */
    _unselectRow: function () {
        var self = this;
        if (this.currentRow === null) {
            return;
        }
        // trigger the save (if the record isn't dirty, the datamodel won't save
        // anything)
        this.trigger_up('field_changed', {
            dataPointID: this.state.data[this.currentRow].id,
            changes: {},
            force_save: true,
        });
        this.trigger_up('change_mode', {mode: 'readonly'});
        var widgets = _.where(this.widgets, {__rowIndex: this.currentRow});
        _.each(widgets, function (widget) {
            self._setCellValue(self.currentRow, widget.__colIndex, true);
            widget.destroy();
        });
        self.widgets = _.without(self.widgets, widgets);
        var $row = this.$('tbody tr').eq(this.currentRow);
        $row.removeClass('o_selected_row');
        $row.find('td').removeClass('o_edit_mode');
        this.currentRow = null;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This method is called when we click on the 'Add an Item' button in a sub
     * list such as a one2many in a form view.
     *
     * @param {MouseEvent} event
     */
    _onAddRecord: function (event) {
        // we don't want the browser to navigate to a the # url
        event.preventDefault();
        // we don't want the click to cause other effects, such as unselecting
        // the row that we are creating, because it counts as a click on a tr
        event.stopPropagation();

        this.trigger_up('add_record');
    },
    /**
     * When the user clicks on a cell, we simply select it.
     *
     * @private
     * @param {MouseEvent} event
     */
    _onCellClick: function (event) {
        // The special_click property explicitely allow events to bubble all
        // the way up to bootstrap's level rather than being stopped earlier.
        if (this.mode === 'readonly' || !this.editable || $(event.target).prop('special_click')) {
            return;
        }
        var $td = $(event.currentTarget);
        var rowIndex = $td.parent().data('index');
        var colIndex = $td.data('index');
        if (colIndex !== undefined && rowIndex !== undefined) {
            this._selectCell(rowIndex, colIndex);
        }
    },
    /**
     * If the list view editable, just let the event bubble. We don't want to
     * open the record in this case anyway.
     *
     * @override
     * @private
     */
    _onRowClicked: function () {
        if (this.mode === 'readonly' || !this.editable) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * We need to manually unselect row, because noone else would do it
     */
    _onEmptyRowClick: function (event) {
        this._unselectRow();
    },
    /**
     * We react to field_changed events by adding the .o_field_dirty css class,
     * which changes its style to a visible orange outline.  It allows the user
     * to have a visual feedback on which fields changed, and on which fields
     * have been saved.
     *
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        var $td = event.target.$el.parent();
        $td.addClass('o_field_dirty');
    },
    /**
     * Clicking on a footer should unselect (and save) the currently selected
     * row.  It has to be done this way, because this is a click inside this.el,
     * and _onWindowClicked ignore those clicks.
     */
    _onFooterClick: function () {
        this._unselectRow();
    },
    /**
     * Move the cursor on the cell just down the current cell.
     */
    _onMoveDown: function () {
        if (this.currentRow < this.state.data.length - 1) {
            this._selectCell(this.currentRow + 1, this.currentCol);
        }
    },
    /**
     * Move the cursor on the left, if possible
     */
    _onMoveLeft: function () {
        if (this.currentCol > 0) {
            this._selectCell(this.currentRow, this.currentCol - 1);
        }
    },
    /**
     * Move the cursor on the next available cell, so either the next available
     * cell on the right, or the first on the next line.  This method is called
     * when the user press the TAB key.
     */
    _onMoveNext: function () {
        if (this.currentCol < this.columns.length - 1) {
            this._selectCell(this.currentRow, this.currentCol + 1);
        } else if (this.currentRow < this.state.data.length - 1) {
            this._selectCell(this.currentRow + 1, 0);
        }
    },
    /**
     * Move the cursor one the beginning of the next line, if possible. This is
     * called when the user press the ENTER key.
     */
    _onMoveNextLine: function () {
        if (this.currentRow < this.state.data.length - 1) {
            this._selectCell(this.currentRow + 1, 0);
        }
    },
    /**
     * Move the cursor one cell right, if possible
     */
    _onMoveRight: function () {
        if (this.currentCol < this.columns.length - 1) {
            this._selectCell(this.currentRow, this.currentCol + 1);
        }
    },
    /**
     * Move the cursor one line up
     */
    _onMoveUp: function () {
        if (this.currentRow > 0) {
            this._selectCell(this.currentRow - 1, this.currentCol);
        }
    },
    /**
     * Triggers a delete event. I don't know why we stop the propagation of the
     * event.
     *
     * @param {MouseEvent} event
     */
    _onTrashIconClick: function (event) {
        event.stopPropagation();
        var id = $(event.target).closest('tr').data('id');
        this.trigger_up('list_record_delete', {id: id});
    },
    /**
     * When a click happens outside the list view, or outside a currently
     * selected row, we want to unselect it.
     *
     * This is quite tricky, because in many cases, such as an autocomplete
     * dropdown opened by a many2one in a list editable row, we actually don't
     * want to unselect (and save) the current row.
     *
     * So, we try to ignore clicks on subelements of the renderer that are
     * appended in the body, outside the table)
     *
     * @param {MouseEvent} event
     */
    _onWindowClicked: function (event) {
        // ignore clicks if this renderer is not in the dom.
        if (!document.contains(this.el)) {
            return;
        }

        // there is currenctly no selected row
        if (this.currentRow === null) {
            return;
        }

        // ignore clicks in autocomplete dropdowns
        if ($(event.target).parents('.ui-autocomplete').length) {
            return;
        }

        // ignore clicks in modals, except if the list is in a modal, and the
        // click is performed in that modal
        var $listModal = this.$el.closest('.modal');
        if ($listModal.length) {
            var $click_modal = $(event.target).parents('.modal');
            if ($click_modal.prop('id') === $listModal.prop('id')) {
                return;
            }
        }

        // ignore clicks if target is no longer in dom.  For example, a click on
        // the 'delete' trash icon of a m2m tag.
        if (!document.contains(event.target)) {
            return;
        }

        // ignore clicks if target is inside the list. In that case, they are
        // handled directly by the renderer.
        if (this.el.contains(event.target) && this.el !== event.target) {
            return;
        }

        this._unselectRow();
    },

});

});
