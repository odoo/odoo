odoo.define('web.EditableListRenderer', function (require) {
"use strict";

/**
 * Editable List renderer
 *
 * The list renderer is reasonably complex, so we split it in two files. This
 * file simply 'includes' the basic ListRenderer to add all the necessary
 * behaviors to enable editing records.
 *
 * Unlike Odoo v10 and before, this list renderer is independant from the form
 * view. It uses the same widgets, but the code is totally stand alone.
 */
var core = require('web.core');
var ListRenderer = require('web.ListRenderer');

var _t = core._t;

ListRenderer.include({
    custom_events: _.extend({}, ListRenderer.prototype.custom_events, {
        move_down: '_onMoveDown',
        move_up: '_onMoveUp',
        move_left: '_onMoveLeft',
        move_right: '_onMoveRight',
        move_next_line: '_onMoveNextLine',
    }),
    events: _.extend({}, ListRenderer.prototype.events, {
        'click tbody td.o_data_cell': '_onCellClick',
        'click tbody tr:not(.o_data_row)': '_onEmptyRowClick',
        'click tfoot': '_onFooterClick',
        'click tr .o_list_record_delete': '_onTrashIconClick',
        'click .o_form_field_x2many_list_row_add a': '_onAddRecord',
    }),
    /**
     * @override
     * @param {Object} params
     * @param {boolean} params.addCreateLine
     * @param {boolean} params.addTrashIcon
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);

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
     * If the given recordID is the list main one (or that no recordID is
     * given), then the whole view can be saved if one of the two following
     * conditions is true:
     * - There is no line in edition (all lines are saved so they are all valid)
     * - The line in edition can be saved
     *
     * @override
     * @param {string} [recordID]
     * @returns {string[]}
     */
    canBeSaved: function (recordID) {
        if ((recordID || this.state.id) === this.state.id) {
            recordID = this.getEditableRecordID();
            if (recordID === null) {
                return [];
            }
        }
        return this._super(recordID);
    },
    /**
     * @see BasicRenderer.confirmChange
     *
     * We also react to changes by adding the 'o_field_dirty' css class,
     * which changes its style to a visible orange outline. It allows the user
     * to have a visual feedback on which fields changed, and on which fields
     * have been saved.
     *
     * @todo maybe should be a basic behavior
     *
     * @override
     * @param {Object} state - a record resource (the new full state)
     * @param {string} id - the local id for the changed record
     * @param {string[]} fields - list of modified fields
     * @param {OdooEvent} e - the event that triggered the change
     * @returns {Deferred}
     */
    confirmChange: function (state, id, fields, e) {
        return this._super.apply(this, arguments).then(function (resetWidgets) {
            _.each(resetWidgets, function (widget) {
                var $td = widget.$el.parent();
                $td.addClass('o_field_dirty');
            });
        });
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
        this.setRowMode(savedRecordID, 'readonly');
    },
    /**
     * Edit a given record in the list
     *
     * @param {string} recordID
     */
    editRecord: function (recordID) {
        var rowIndex = _.findIndex(this.state.data, {id: recordID});
        this._selectCell(rowIndex, 0);
    },
    /**
     * Returns the recordID associated to the line which is currently in edition
     * or null if there is no line in edition.
     *
     * @returns {string|null}
     */
    getEditableRecordID: function () {
        if (this.currentRow !== null) {
            return this.state.data[this.currentRow].id;
        }
        return null;
    },
    /**
     * Removes the line associated to the given recordID (the index of the row
     * is found thanks to the old state), then updates the state.
     *
     * @param {Object} state
     * @param {string} recordID
     */
    removeLine: function (state, recordID) {
        var rowIndex = _.findIndex(this.state.data, {id: recordID});
        if (rowIndex === this.currentRow) {
            this.currentRow = null;
        }
        var $row = this.$('.o_data_row:nth(' + rowIndex + ')');
        $row.remove();

        this.state = state;
    },
    /**
     * Updates the already rendered row associated to the given recordID so that
     * it fits the given mode.
     *
     * @param {string} recordID
     * @param {string} mode
     * @param {boolean} [keepDirtyFlag=false]
     */
    setRowMode: function (recordID, mode, keepDirtyFlag) {
        var self = this;
        var rowIndex = _.findIndex(this.state.data, {id: recordID});
        if (rowIndex < 0) {
            return;
        }
        var editMode = (mode === 'edit');
        var record = this.state.data[rowIndex];

        this.currentRow = editMode ? rowIndex : null;
        var $row = this.$('.o_data_row:nth(' + rowIndex + ')');
        $row.toggleClass('o_selected_row', editMode);

        if (editMode) {
            // Instantiate column widgets and destroy potential readonly ones
            var oldWidgets = _.clone(this.allFieldWidgets[record.id]);
            var $tds = $row.children('.o_data_cell');
            _.each(this.columns, function (node, colIndex) {
                var $td = $tds.eq(colIndex);
                var $newTd = self._renderBodyCell(record, node, colIndex, {
                    renderInvisible: true,
                    renderWidgets: true,
                });

                // TODO this is ugly...
                if ($td.hasClass('o_list_button')) {
                    self._unregisterModifiersElement(node, record, $td.children());
                }

                // Force the width of each cell to its current value so that it
                // won't change if its content changes, to prevent the view from
                // flickering
                $td.width($td.width());
                $td.empty().append($newTd.contents());
            });
            _.each(oldWidgets, this._destroyFieldWidget.bind(this, record));
        } else {
            for (var colIndex = 0; colIndex < this.columns.length; colIndex++) {
                this._setCellValue(rowIndex, colIndex, keepDirtyFlag || false);
            }
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
     * Move the cursor one the beginning of the next line, if possible.
     * If there is no next line, then we create a new record.
     *
     * @private
     */
    _moveToNextLine: function () {
        if (this.currentRow < this.state.data.length - 1) {
            this._selectCell(this.currentRow + 1, 0);
        } else {
            this._unselectRow().then(
                this.trigger_up.bind(this, 'add_record')
            );
        }
    },
    /**
     * @override
     * @returns {Deferred}
     */
    _render: function () {
        this.currentRow = null;
        this.currentCol = null;
        return this._super.apply(this, arguments);
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
     * Editable rows are possibly extended with a trash icon on their right, to
     * allow deleting the corresponding record.
     *
     * @override
     * @param {any} record
     * @param {any} index
     * @returns {jQueryElement}
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);
        if (this.addTrashIcon) {
            var $icon = $('<span>', {class: 'fa fa-trash-o', name: 'delete'});
            var $td = $('<td>', {class: 'o_list_record_delete'}).append($icon);
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
     * @override
     * @private
     * @returns {Deferred} this deferred is resolved immediately
     */
    _renderView: function () {
        this.currentRow = null;
        return this._super.apply(this, arguments);
    },
    /**
     * This is one of the trickiest method in the editable renderer.  It has to
     * do a lot of stuff: it has to determine which cell should be selected (if
     * the target cell is readonly, we need to find another suitable cell), then
     * unselect the current row, and activate the line where the selected cell
     * is, if necessary.
     *
     * @param {integer} rowIndex
     * @param {integer} colIndex
     */
    _selectCell: function (rowIndex, colIndex) {
        // Do nothing if the user tries to select current cell
        if (rowIndex === this.currentRow && colIndex === this.currentCol) {
            return;
        }

        // Select the row then activate the widget in the correct cell
        var self = this;
        this._selectRow(rowIndex).then(function () {
            var record = self.state.data[rowIndex];
            var fieldIndex = self._activateFieldWidget(record, colIndex - getNbButtonBefore(colIndex));

            // If no widget to activate in the row, unselect the row
            if (fieldIndex < 0) {
                return self._unselectRow();
            }

            self.currentCol = fieldIndex + getNbButtonBefore(fieldIndex);

            function getNbButtonBefore(index) {
                var nbButtons = 0;
                for (var i = 0 ; i < index ; i++) {
                    if (self.columns[i].tag === 'button') {
                        nbButtons++;
                    }
                }
                return nbButtons;
            }
        });
    },
    /**
     * Activates the row at the given row index.
     *
     * @param {integer} rowIndex
     */
    _selectRow: function (rowIndex) {
        // Do nothing if already selected
        if (rowIndex === this.currentRow) {
            return $.when();
        }

        // To select a row, the currently selected one must be unselected first
        var self = this;
        return this._unselectRow().then(function () {
            // Notify the controller we want to make a record editable
            var record = self.state.data[rowIndex];
            self.trigger_up('edit_line', {
                recordID: record.id,
            });
        });
    },
    /**
     * Set the value of a cell.  This method can be called when the value of a
     * cell was modified, for example after an onchange.
     *
     * @param {integer} rowIndex
     * @param {integer} colIndex
     * @param {boolean} keepDirtyFlag
     */
    _setCellValue: function (rowIndex, colIndex, keepDirtyFlag) {
        var record = this.state.data[rowIndex];
        var node = this.columns[colIndex];

        var $oldTd = this.$('.o_data_row:nth(' + rowIndex + ') > .o_data_cell:nth(' + colIndex + ')');
        var $newTd = this._renderBodyCell(record, node, colIndex, {mode: 'readonly'});
        if (keepDirtyFlag && $oldTd.hasClass('o_field_dirty')) {
            $newTd.addClass('o_field_dirty');
        }
        this._unregisterModifiersElement(node, record, $oldTd);
        $oldTd.replaceWith($newTd);

        // Destroy old cell field widget if any
        // TODO this is very inefficient O(n^3) instead of O(n) on row update
        // because this method is called for each cell (O(n)), each time we have
        // to find the associated record widget (O(n)) and once found, the
        // search is performed again by the _destroyFieldWidget function
        if (node.tag === 'field') {
            var recordWidgets = this.allFieldWidgets[record.id];
            var w = _.findWhere(recordWidgets, {name: node.attrs.name}); //
            if (w) {
                this._destroyFieldWidget(record, w);
            }
        }
    },
    /**
     * This method is called whenever we click/move outside of a row that was
     * in edit mode. This is the moment we save all accumulated changes on that
     * row, if needed (@see BasicController.saveRecord).
     *
     * @returns {Deferred} The deferred resolves if the row was unselected (and
     *   possibly removed). If may be rejected, when the row is dirty and the
     *   user refuses to discard its changes.
     */
    _unselectRow: function () {
        // Protect against calling this method when no row is selected
        if (this.currentRow === null) {
            return $.when();
        }

        var record = this.state.data[this.currentRow];
        var def = $.Deferred();
        this.trigger_up('save_line', {
            recordID: record.id,
            onSuccess: def.resolve.bind(def),
            onFailure: def.reject.bind(def),
        });
        return def;
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

        // but we do want to unselect current row
        var self = this;
        this._unselectRow().then(function () {
            self.trigger_up('add_record'); // TODO write a test, the deferred was not considered
        });
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
        var $tr = $td.parent();
        var rowIndex = this.$('.o_data_row').index($tr);
        var colIndex = $tr.find('.o_data_cell').index($td);
        this._selectCell(rowIndex, colIndex);
    },
    /**
     * We need to manually unselect row, because noone else would do it
     */
    _onEmptyRowClick: function (event) {
        this._unselectRow();
    },
    /**
     * Clicking on a footer should unselect (and save) the currently selected
     * row. It has to be done this way, because this is a click inside this.el,
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
     *
     * @param {OdooEvent} ev
     */
    _onMoveNext: function (ev) {
        // we need to stop the event, to prevent interference with some other
        // component up there, such as a form renderer.
        ev.stopPropagation();
        if (this.currentCol + 1 < this.columns.length) {
            this._selectCell(this.currentRow, this.currentCol + 1);
        } else {
            this._moveToNextLine();
        }
    },
    /**
     * @private
     * @param {OdooEvent} event
     */
    _onMoveNextLine: function (event) {
        event.stopPropagation();
        this._moveToNextLine();
    },
    /**
     * Move the cursor on the previous available cell, so either the previous
     * available cell on the left, or the last on the previous line. This method
     * is called when the user press the TAB key while holding the shift key.
     *
     * @param {OdooEvent} ev
     */
    _onMovePrevious: function (ev) {
        // we need to stop the event, to prevent interference with some other
        // component up there, such as a form renderer.
        ev.stopPropagation();
        if (this.currentCol > 0) {
            this._selectCell(this.currentRow, this.currentCol - 1);
        } else if (this.currentRow > 0) {
            this._selectCell(this.currentRow - 1, this.columns.length - 1);
        }
    },
    /**
     * Move the cursor one cell right, if possible
     */
    _onMoveRight: function () {
        if (this.currentCol + 1 < this.columns.length) {
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

        // there is currently no selected row
        if (this.currentRow === null) {
            return;
        }

        // ignore clicks in autocomplete dropdowns
        if ($(event.target).parents('.ui-autocomplete').length) {
            return;
        }

        // ignore clicks in modals, except if the list is in a modal, and the
        // click is performed in that modal
        var $clickModal = $(event.target).closest('.modal');
        if ($clickModal.length) {
            var $listModal = this.$el.closest('.modal');
            if ($clickModal.prop('id') !== $listModal.prop('id')) {
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
