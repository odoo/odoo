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
var dom = require('web.dom');
var ListRenderer = require('web.ListRenderer');
var utils = require('web.utils');

var _t = core._t;

ListRenderer.include({
    custom_events: _.extend({}, ListRenderer.prototype.custom_events, {
        navigation_move: '_onNavigationMove',
    }),
    events: _.extend({}, ListRenderer.prototype.events, {
        'click tbody td.o_data_cell': '_onCellClick',
        'click tbody tr:not(.o_data_row)': '_onEmptyRowClick',
        'click tfoot': '_onFooterClick',
        'click tr .o_list_record_delete': '_onTrashIconClick',
        'click .o_field_x2many_list_row_add a': '_onAddRecord',
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

        this.currentRow = null;
        this.currentFieldIndex = null;
    },
    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        // deliberately use the 'editable' attribute instead of '_isEditable'
        // function, because the groupBy must not be taken into account to
        // enable the '_onWindowClicked' handler (otherwise, an editable grouped
        // list which is reloaded without groupBy wouldn't have this handler
        // bound, and edited rows couldn't be left by clicking outside the list)
        if (this.editable) {
            this.$el.css({height: '100%'}); // seems useless: to remove in master
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
     * We need to override the confirmChange method from BasicRenderer to
     * reevaluate the row decorations.  Since they depends on the current value
     * of the row, they might have changed between each edit.
     *
     * @override
     */
    confirmChange: function (state, id) {
        var self = this;
        return this._super.apply(this, arguments).then(function (widgets) {
            if (widgets.length) {
                var rowIndex = _.findIndex(state.data, function (r) {
                    return r.id === id;
                });
                var $row = self.$('.o_data_row:nth(' + rowIndex + ')');
                self._setDecorationClasses(state.data[rowIndex], $row);
                self._updateFooter();
            }
            return widgets;
        });
    },
    /**
     * This is a specialized version of confirmChange, meant to be called when
     * the change may have affected more than one line (so, for example, an
     * onchange which add/remove a few lines in a x2many.  This does not occur
     * in a normal list view)
     *
     * The update is more difficult when other rows could have been changed. We
     * need to potentially remove some lines, add some other lines, update some
     * other lines and maybe reorder a few of them.  This problem would neatly
     * be solved by using a virtual dom, but we do not have this luxury yet.
     * So, in the meantime, what we do is basically remove every current row
     * except the 'main' one (the row which caused the update), then rerender
     * every new row and add them before/after the main one.
     *
     * @param {Object} state
     * @param {string} id
     * @param {string[]} fields
     * @param {OdooEvent} ev
     * @returns {Deferred<AbstractField[]>} resolved with the list of widgets
     *                                      that have been reset
     */
    confirmUpdate: function (state, id, fields, ev) {
        var self = this;

        // store the cursor position to restore it once potential onchanges have
        // been applied
        var currentRowID, currentWidget, focusedElement, selectionRange;
        if (self.currentRow !== null) {
            currentRowID = this.state.data[this.currentRow].id;
            currentWidget = this.allFieldWidgets[currentRowID][this.currentFieldIndex];
            focusedElement = currentWidget.getFocusableElement().get(0);
            if (currentWidget.formatType !== 'boolean') {
                selectionRange = dom.getSelectionRange(focusedElement);
            }
        }

        var oldData = this.state.data;
        this.state = state;
        return this.confirmChange(state, id, fields, ev).then(function () {
            // If no record with 'id' can be found in the state, the
            // confirmChange method will have rerendered the whole view already,
            // so no further work is necessary.
            var record = _.findWhere(state.data, {id: id});
            if (!record) {
                return;
            }
            var oldRowIndex = _.findIndex(oldData, {id: id});
            var $row = self.$('.o_data_row:nth(' + oldRowIndex + ')');
            $row.nextAll('.o_data_row').remove();
            $row.prevAll().remove();
            _.each(oldData, function (rec) {
                if (rec.id !== id) {
                    self._destroyFieldWidgets(rec.id);
                }
            });
            var newRowIndex = _.findIndex(state.data, {id: id});
            var $lastRow = $row;
            _.each(state.data, function (record, index) {
                if (index === newRowIndex) {
                    return;
                }
                var $newRow = self._renderRow(record);
                if (index < newRowIndex) {
                    $newRow.insertBefore($row);
                } else {
                    $newRow.insertAfter($lastRow);
                    $lastRow = $newRow;
                }
            });
            if (self.currentRow !== null) {
                self.currentRow = newRowIndex;
                return self._selectCell(newRowIndex, self.currentFieldIndex, {force: true}).then(function () {
                    // restore the cursor position
                    currentRowID = self.state.data[newRowIndex].id;
                    currentWidget = self.allFieldWidgets[currentRowID][self.currentFieldIndex];
                    focusedElement = currentWidget.getFocusableElement().get(0);
                    if (selectionRange) {
                        dom.setSelectionRange(focusedElement, selectionRange);
                    }
                });
            }
        });
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
        var self = this;
        var rowIndex = _.findIndex(this.state.data, {id: recordID});
        this.state = state;
        if (rowIndex === -1) {
            return;
        }
        if (rowIndex === this.currentRow) {
            this.currentRow = null;
        }

        // remove the row
        var $row = this.$('.o_data_row:nth(' + rowIndex + ')');
        if (this.state.count >= 4) {
            $row.remove();
        } else {
            $row.replaceWith(this._renderEmptyRow());
        }

        this._destroyFieldWidgets(recordID);
    },
    /**
     * Updates the already rendered row associated to the given recordID so that
     * it fits the given mode.
     *
     * @param {string} recordID
     * @param {string} mode
     * @returns {Deferred}
     */
    setRowMode: function (recordID, mode) {
        var self = this;

        // find the record and its row index (handles ungrouped and grouped cases
        // as even if the grouped list doesn't support edition, it may contain
        // a widget allowing the edition in readonly (e.g. priority), so it
        // should be able to update a record as well)
        var record;
        var rowIndex;
        if (this.state.groupedBy.length) {
            rowIndex = -1;
            var count = 0;
            utils.traverse_records(this.state, function (r) {
                if (r.id === recordID) {
                    record = r;
                    rowIndex = count;
                }
                count++;
            });
        } else {
            rowIndex = _.findIndex(this.state.data, {id: recordID});
            record = this.state.data[rowIndex];
        }

        if (rowIndex < 0) {
            return $.when();
        }
        var editMode = (mode === 'edit');

        this.currentRow = editMode ? rowIndex : null;
        var $row = this.$('.o_data_row:nth(' + rowIndex + ')');
        var $tds = $row.children('.o_data_cell');
        var oldWidgets = _.clone(this.allFieldWidgets[record.id]);

        // When switching to edit mode, force the dimensions of all cells to
        // their current value so that they won't change if their content
        // changes, to prevent the view from flickering.
        if (editMode) {
            $tds.each(function () {
                var $td = $(this);
                $td.css({width: $td.outerWidth()});
            });
        }

        // Prepare options for cell rendering (this depends on the mode)
        var options = {
            renderInvisible: editMode,
            renderWidgets: editMode,
        };
        options.mode = editMode ? 'edit' : 'readonly';

        // Switch each cell to the new mode; note: the '_renderBodyCell'
        // function might fill the 'this.defs' variables with multiple deferred
        // so we create the array and delete it after the rendering.
        var defs = [];
        this.defs = defs;
        _.each(this.columns, function (node, colIndex) {
            var $td = $tds.eq(colIndex);
            var $newTd = self._renderBodyCell(record, node, colIndex, options);

            // Widgets are unregistered of modifiers data when they are
            // destroyed. This is not the case for simple buttons so we have to
            // do it here.
            if ($td.hasClass('o_list_button')) {
                self._unregisterModifiersElement(node, recordID, $td.children());
            }

            // For edit mode we only replace the content of the cell with its
            // new content (invisible fields, editable fields, ...).
            // For readonly mode, we replace the whole cell so that the
            // dimensions of the cell are not forced anymore.
            if (editMode) {
                $td.empty().append($newTd.contents());
            } else {
                self._unregisterModifiersElement(node, recordID, $td);
                $td.replaceWith($newTd);
            }
        });
        delete this.defs;

        // Destroy old field widgets
        _.each(oldWidgets, this._destroyFieldWidget.bind(this, recordID));

        // Toggle selected class here so that style is applied at the end
        $row.toggleClass('o_selected_row', editMode);

        return $.when.apply($, defs);
    },
    /**
     * This method is called whenever we click/move outside of a row that was
     * in edit mode. This is the moment we save all accumulated changes on that
     * row, if needed (@see BasicController.saveRecord).
     *
     * Note that we have to disable the focusable elements (inputs, ...) to
     * prevent subsequent editions. These edits would be lost, because the list
     * view only saves records when unselecting a row.
     *
     * @returns {Deferred} The deferred resolves if the row was unselected (and
     *   possibly removed). If may be rejected, when the row is dirty and the
     *   user refuses to discard its changes.
     */
    unselectRow: function () {
        // Protect against calling this method when no row is selected
        if (this.currentRow === null) {
            return $.when();
        }

        var record = this.state.data[this.currentRow];
        var recordWidgets = this.allFieldWidgets[record.id];
        toggleWidgets(true);

        var def = $.Deferred();
        this.trigger_up('save_line', {
            recordID: record.id,
            onSuccess: def.resolve.bind(def),
            onFailure: def.reject.bind(def),
        });
        return def.fail(toggleWidgets.bind(null, false));

        function toggleWidgets(disabled) {
            _.each(recordWidgets, function (widget) {
                var $el = widget.getFocusableElement();
                $el.prop('disabled', disabled);
            });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Destroy all field widgets corresponding to a record.  Useful when we are
     * removing a useless row.
     *
     * @param {string} recordID
     */
    _destroyFieldWidgets: function (recordID) {
        if (recordID in this.allFieldWidgets) {
            var widgetsToDestroy = this.allFieldWidgets[recordID].slice();
            _.each(widgetsToDestroy, this._destroyFieldWidget.bind(this, recordID));
            delete this.allFieldWidgets[recordID];
        }
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
     * Returns true iff the list is editable, i.e. if it isn't grouped and if
     * the editable attribute is set on the root node of its arch.
     *
     * @private
     * @returns {boolean}
     */
    _isEditable: function () {
        return !this.state.groupedBy.length && this.editable;
    },
    /**
     * Move the cursor on the end of the previous line, if possible.
     * If there is no previous line, then we create a new record.
     *
     * @private
     */
    _moveToPreviousLine: function () {
        if (this.currentRow > 0) {
            this._selectCell(this.currentRow - 1, this.columns.length - 1);
        } else {
            this.unselectRow().then(this.trigger_up.bind(this, 'add_record'));
        }
    },
    /**
     * Move the cursor on the beginning of the next line, if possible.
     * If there is no next line, then we create a new record.
     *
     * @private
     */
    _moveToNextLine: function () {
        var record = this.state.data[this.currentRow];
        var fieldNames = this.canBeSaved(record.id);
        if (fieldNames.length) {
            return;
        }

        if (this.currentRow < this.state.data.length - 1) {
            this._selectCell(this.currentRow + 1, 0);
        } else {
            var self = this;
            this.unselectRow().then(function () {
                self.trigger_up('add_record', {
                    onFail: self._selectCell.bind(self, 0, 0, {}),
                });
            });
        }
    },
    /**
     * @override
     * @returns {Deferred}
     */
    _render: function () {
        this.currentRow = null;
        this.currentFieldIndex = null;
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
        if (this.hasHandle) {
            $body.sortable({
                axis: 'y',
                items: '> tr.o_data_row',
                helper: 'clone',
                handle: '.o_row_handle',
                stop: this._resequence.bind(this),
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
            var $icon = $('<button>', {class: 'fa fa-trash-o o_list_record_delete_btn', name: 'delete',
                'aria-label': _t('Delete row ') + (index+1)});
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
                        .addClass('o_field_x2many_list_row_add')
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
        var self = this;
        this.currentRow = null;
        return this._super.apply(this, arguments).then(function () {
            if (self._isEditable()) {
                self.$('table').addClass('o_editable_list');
            }
        });
    },
    /**
     * Force the resequencing of the items in the list.
     *
     * @private
     * @param {jQuery.Event} event
     * @param {Object} ui jqueryui sortable widget
     */
    _resequence: function (event, ui) {
        var self = this;
        var movedRecordID = ui.item.data('id');
        var rows = this.state.data;
        var row = _.findWhere(rows, {id: movedRecordID});
        var index0 = rows.indexOf(row);
        var index1 = ui.item.index();
        var lower = Math.min(index0, index1);
        var upper = Math.max(index0, index1) + 1;

        var order = _.findWhere(self.state.orderedBy, {name: self.handleField});
        var asc = !order || order.asc;
        var reorderAll = false;
        var sequence = (asc ? -1 : 1) * Infinity;

        // determine if we need to reorder all lines
        _.each(rows, function (row, index) {
            if ((index < lower || index >= upper) &&
                ((asc && sequence >= row.data[self.handleField]) ||
                 (!asc && sequence <= row.data[self.handleField]))) {
                reorderAll = true;
            }
            sequence = row.data[self.handleField];
        });

        if (reorderAll) {
            rows = _.without(rows, row);
            rows.splice(index1, 0, row);
        } else {
            rows = rows.slice(lower, upper);
            rows = _.without(rows, row);
            if (index0 > index1) {
                rows.unshift(row);
            } else {
                rows.push(row);
            }
        }

        var sequences = _.pluck(_.pluck(rows, 'data'), self.handleField);
        var rowIDs = _.pluck(rows, 'id');

        if (!asc) {
            rowIDs.reverse();
        }
        this.unselectRow().then(function () {
            self.trigger_up('resequence', {
                rowIDs: rowIDs,
                offset: _.min(sequences),
                handleField: self.handleField,
            });
        });
    },
    /**
     * This is one of the trickiest method in the editable renderer.  It has to
     * do a lot of stuff: it has to determine which cell should be selected (if
     * the target cell is readonly, we need to find another suitable cell), then
     * unselect the current row, and activate the line where the selected cell
     * is, if necessary.
     *
     * @param {integer} rowIndex
     * @param {integer} fieldIndex
     * @param {Object} [options]
     * @param {Event} [options.event] original target of the event which
     * @param {boolean} [options.wrap=true] if true and no widget could be
     *   triggered the cell selection
     *   selected from the fieldIndex to the last column, then we wrap around and
     *   try to select a widget starting from the beginning
     * @param {boolean} [options.force=false] if true, force selecting the cell
     *   even if seems to be already the selected one (useful after a re-
     *   rendering, to reset the focus on the correct field)
     * @return {Deferred} fails if no cell could be selected
     */
    _selectCell: function (rowIndex, fieldIndex, options) {
        options = options || {};
        // Do nothing if the user tries to select current cell
        if (!options.force && rowIndex === this.currentRow && fieldIndex === this.currentFieldIndex) {
            return $.when();
        }
        var wrap = options.wrap === undefined ? true : options.wrap;

        // Select the row then activate the widget in the correct cell
        var self = this;
        return this._selectRow(rowIndex).then(function () {
            var record = self.state.data[rowIndex];
            if (fieldIndex >= (self.allFieldWidgets[record.id] || []).length) {
                return $.Deferred().reject();
            }
            // _activateFieldWidget might trigger an onchange,
            // which requires currentFieldIndex to be set
            // so that the cursor can be restored
            var oldFieldIndex = self.currentFieldIndex;
            self.currentFieldIndex = fieldIndex;
            fieldIndex = self._activateFieldWidget(record, fieldIndex, {
                inc: 1,
                wrap: wrap,
                event: options && options.event,
            });
            if (fieldIndex < 0) {
                self.currentFieldIndex = oldFieldIndex;
                return $.Deferred().reject();
            }
            self.currentFieldIndex = fieldIndex;
        });
    },
    /**
     * Activates the row at the given row index.
     *
     * @param {integer} rowIndex
     * @returns {Deferred}
     */
    _selectRow: function (rowIndex) {
        // Do nothing if already selected
        if (rowIndex === this.currentRow) {
            return $.when();
        }

        // To select a row, the currently selected one must be unselected first
        var self = this;
        return this.unselectRow().then(function () {
            if (self.state.data.length <= rowIndex) {
                // The row to selected doesn't exist anymore (probably because
                // an onchange triggered when unselecting the previous one
                // removes rows)
                return $.Deferred().reject();
            }
            // Notify the controller we want to make a record editable
            var def = $.Deferred();
            self.trigger_up('edit_line', {
                index: rowIndex,
                onSuccess: def.resolve.bind(def),
            });
            return def;
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
        var self = this;
        this.unselectRow().then(function () {
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
        if (!this._isEditable() || $(event.target).prop('special_click')) {
            return;
        }
        var $td = $(event.currentTarget);
        var $tr = $td.parent();
        var rowIndex = this.$('.o_data_row').index($tr);
        var fieldIndex = Math.max($tr.find('.o_data_cell').not('.o_list_button').index($td), 0);
        this._selectCell(rowIndex, fieldIndex, {event: event});
    },
    /**
     * We need to manually unselect row, because noone else would do it
     */
    _onEmptyRowClick: function () {
        this.unselectRow();
    },
    /**
     * Clicking on a footer should unselect (and save) the currently selected
     * row. It has to be done this way, because this is a click inside this.el,
     * and _onWindowClicked ignore those clicks.
     */
    _onFooterClick: function () {
        this.unselectRow();
    },
    /**
     * Handles the keyboard navigation according to events triggered by field
     * widgets.
     * - up/down: move to the cell above/below if any, or the first activable
     *          one on the row above/below if any on the right of this cell
     *          above/below (if none on the right, wrap to the beginning of the
     *          line).
     * - left/right: move to the first activable cell on the left/right if any
     *          (wrap to the end/beginning of the line if necessary).
     * - previous: move to the first activable cell on the left if any, if not
     *          move to the rightmost activable cell on the row above.
     * - next: move to the first activable cell on the right if any, if not move
     *          to the leftmost activable cell on the row below.
     * - next_line: move to leftmost activable cell on the row below.
     *
     * Note: moving to a line below if on the last line or moving to a line
     * above if on the first line automatically creates a new line.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        ev.stopPropagation(); // stop the event, the action is done by this renderer
        switch (ev.data.direction) {
            case 'up':
                if (this.currentRow > 0) {
                    this._selectCell(this.currentRow - 1, this.currentFieldIndex);
                }
                break;
            case 'right':
                if (this.currentFieldIndex + 1 < this.columns.length) {
                    this._selectCell(this.currentRow, this.currentFieldIndex + 1);
                }
                break;
            case 'down':
                if (this.currentRow < this.state.data.length - 1) {
                    this._selectCell(this.currentRow + 1, this.currentFieldIndex);
                }
                break;
            case 'left':
                if (this.currentFieldIndex > 0) {
                    this._selectCell(this.currentRow, this.currentFieldIndex - 1);
                }
                break;
            case 'previous':
                if (this.currentFieldIndex > 0) {
                    this._selectCell(this.currentRow, this.currentFieldIndex - 1, {wrap: false})
                        .fail(this._moveToPreviousLine.bind(this));
                } else {
                    this._moveToPreviousLine();
                }
                break;
            case 'next':
                if (this.currentFieldIndex + 1 < this.columns.length) {
                    this._selectCell(this.currentRow, this.currentFieldIndex + 1, {wrap: false})
                        .fail(this._moveToNextLine.bind(this));
                } else {
                    this._moveToNextLine();
                }
                break;
            case 'next_line':
                this._moveToNextLine();
                break;
            case 'cancel':
                // stop the original event (typically an ESCAPE keydown), to
                // prevent from closing the potential dialog containing this list
                ev.data.originalEvent.stopPropagation();
                this.trigger_up('discard_changes', {
                    recordID: ev.target.dataPointID,
                });
                break;
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
        if (!this._isEditable()) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Overrides to prevent from sorting if we are currently editing a record.
     *
     * @override
     * @private
     */
    _onSortColumn: function () {
        if (this.currentRow === null) {
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
        var $row = $(event.target).closest('tr')
        var id = $row.data('id');
        if ($row.hasClass('o_selected_row')) {
            this.trigger_up('list_record_delete', {id: id});
        } else {
            var self = this;
            this.unselectRow().then(function () {
                self.trigger_up('list_record_delete', {id: id});
            });
        }
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

        this.unselectRow();
    },
});

});
