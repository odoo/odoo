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
var Dialog = require('web.Dialog');
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
        'click tbody td': '_onCellClick',
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

        // the dirtyRows object is there to keep track of lines that have been
        // modified by the user
        this.dirtyRows = {};
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
     * @returns {Deferred}
     */
    canBeSaved: function () {
        var self = this;
        var invalidDirtyWidgets = [];
        var invalidCleanWidgets = [];
        _.each(this.allFieldWidgets, function (recordWidgets, recordID) {
            _.each(recordWidgets, function (widget) {
                // Note: the _canWidgetBeSaved method may return a deferred in
                // general, but not in this case. Here, this method is called by
                // a fieldone2many when it needs to make sure the state is
                // valid. So, the widgets that we consider here are widgets that
                // can be in a one2many, and we don't support a list inside a
                // list (for now at least).
                if (!self._canWidgetBeSaved(widget)) {
                    if (self.dirtyRows[recordID]) {
                        invalidDirtyWidgets.push(widget);
                    } else {
                        invalidCleanWidgets.push(widget);
                    }
                }
            });
        });
        if (invalidDirtyWidgets.length) {
            // TODO: ask for confirmation, open dialog, and depending on user
            // input, resolve and reject deferred
        }
        if (invalidCleanWidgets.length) {
            this._unselectRow();
        }
        return $.when();
    },
    /**
     * @see BasicRenderer.confirmChange
     *
     * We also react to changes by adding the 'o_field_dirty' css class,
     * which changes its style to a visible orange outline. It allows the user
     * to have a visual feedback on which fields changed, and on which fields
     * have been saved.
     *
     * @override
     * @param {Object} state - a record resource (the new full state)
     * @param {string} id - the local id for the changed record
     * @param {string[]} fields - list of modified fields
     * @param {OdooEvent} e - the event that triggered the change
     * @returns {Deferred}
     */
    confirmChange: function (state, id, fields, e) {
        this.dirtyRows[id] = true;

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
        return $row.children(':nth(' + (index + (this.hasSelectors ? 1 : 0)) + ')');
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
     * @param {Object} [options]
     * @returns {jQueryElement}
     */
    _renderBodyCell: function (record, node, index, options) {
        var $cell = this._super.apply(this, arguments);
        if (this.mode === 'readonly') {
            return $cell;
        }
        return $cell.data('index', index);
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

        var record = this.state.data[rowIndex];

        // If this is a different row, then we need to prepare for it by
        // unselecting the current row and selecting the new one.
        var def = $.when();
        if (rowIndex !== this.currentRow) {
            def = this._unselectRow(); // This will trigger the save
            def.then(this._selectRow.bind(this, rowIndex));
        }

        // In all cases (new row or not), activate the proper column widget
        var self = this;
        def.then(function () {
            var fieldIndex = self._activateFieldWidget(record, colIndex - getNbButtonBefore(colIndex));
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
        this.currentRow = rowIndex;

        var self = this;
        var record = this.state.data[rowIndex];

        // Force the width of each cell to its current value so that it won't
        // change if its content changes, to prevent the view from flickering
        var $row = this.$('tbody > tr:nth(' + rowIndex + ')');
        $row.addClass('o_selected_row');
        $row.children().each(function () {
            var $td = $(this);
            $td.width($td.width());
        });

        // Instantiate column widgets and destroy potential readonly ones
        var oldWidgets = _.clone(this.allFieldWidgets[record.id]);
        _.each(this.columns, function (node, index) {
            var $newTd = self._renderBodyCell(record, node, index, {
                renderInvisible: true,
                renderWidgets: true,
            });
            var $td = self._findTd($row, index);
            if ($td.hasClass('o_list_button')) {
                self._unregisterModifiersElement(node, record, $td.children()); // FIXME this is ugly...
            }
            $td.empty().append($newTd.contents());
        });
        _.each(oldWidgets, this._destroyFieldWidget.bind(this, record));

        this.trigger_up('change_mode', {mode: 'edit'});
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
        var $oldTd = this._findTd(this.$('tbody > tr:nth(' + rowIndex + ')'), colIndex);
        var $newTd = this._renderBodyCell(record, node, colIndex, {mode: 'readonly'});
        if (keepDirtyFlag && $oldTd.hasClass('o_field_dirty')) {
            $newTd.addClass('o_field_dirty');
        }
        this._unregisterModifiersElement(node, record, $oldTd);
        $oldTd.replaceWith($newTd);
    },
    /**
     * This method is called whenever we click/move outside of a row that was
     * in edit mode. This is the moment we save all accumulated changes on that
     * row, if needed.
     *
     * If the current row is valid, then it can be unselected. If it is not
     * valid, we need to check if it is dirty. If it is not dirty, it can be
     * unselected (and will be removed). If it is dirty, we need to ask the user
     * for confirmation. If the user agrees, the row will be removed, otherwise
     * nothing happens (it is still selected)
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

        var self = this;
        var record = this.state.data[this.currentRow];
        var rowWidgets = _.clone(this.allFieldWidgets[record.id]);
        var isRowValid = _.every(rowWidgets, this._canWidgetBeSaved.bind(this));
        var $row = this.$('tbody > tr.o_selected_row');

        // If the row is not valid and is dirty, we have to ask the user
        // confirmation before going further
        var def = $.when();
        if (!isRowValid && this.dirtyRows[record.id]) {
            def = $.Deferred();
            var message = _t("The line has been modified, your changes will be discarded. Are you sure you want to discard the changes ?");
            var dialog = Dialog.confirm(this, message, {
                title: _t("Warning"),
                confirm_callback: def.resolve.bind(def),
                cancel_callback: def.reject.bind(def),
            });
            dialog.$modal.on('hidden.bs.modal', def.reject.bind(def));
        }

        return def.then(function finalizeUnselect() {
            var rowRemoved = false;
            var keepDirtyFlag = true;
            if (isRowValid) {
                // Trigger the save (if the record isn't dirty, the datamodel
                // won't save anything)
                self.trigger_up('field_changed', {
                    dataPointID: record.id,
                    changes: {},
                    force_save: true,
                });
            } else if (record.res_id) {
                // Not a creation, tell the model to discard the changes
                self.trigger_up('discard_changes', {id: record.id});
                keepDirtyFlag = false;
            } else {
                // Creation, tell the model to discard the row and remove the
                // associated row DOM element
                self.trigger_up('discard_line', {id: record.id});
                $row.remove(); // FIXME row indexes are not updated... let's remove data('index') and check index dynamically ?
                rowRemoved = true;
            }

            // Update row if it was not removed
            if (!rowRemoved) {
                $row.removeClass('o_selected_row');
                _.each(self.columns, function (col, colIndex) {
                    self._setCellValue(self.currentRow, colIndex, keepDirtyFlag);
                });
            }

            // Destroy the edition widgets
            _.each(rowWidgets, self._destroyFieldWidget.bind(self, record));

            delete self.dirtyRows[record.id];
            self.currentRow = null;
            self.trigger_up('change_mode', {mode: 'readonly'});
        });
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
        this._unselectRow();

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
        } else {
            this._unselectRow();
            this.trigger_up('add_record');
        }
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
