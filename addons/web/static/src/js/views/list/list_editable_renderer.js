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
        'click .o_field_x2many_list_row_add a': '_onAddRecord',
        'click .o_group_field_row_add a': '_onAddRecordToGroup',
        'keydown .o_field_x2many_list_row_add a': '_onKeyDownAddRecord',
        'click tbody td.o_data_cell': '_onCellClick',
        'click tbody tr:not(.o_data_row)': '_onEmptyRowClick',
        'click tfoot': '_onFooterClick',
        'click tr .o_list_record_remove': '_onRemoveIconClick',
    }),
    /**
     * @override
     * @param {Object} params
     * @param {boolean} params.addCreateLine
     * @param {boolean} params.addCreateLineInGroups
     * @param {boolean} params.addTrashIcon
     * @param {boolean} params.isMany2Many
     */
    init: function (parent, state, params) {
        var self = this;
        this._super.apply(this, arguments);

        // if addCreateLine (resp. addCreateLineInGroups) is true, the renderer
        // will add a 'Add a line' link at the bottom of the list view (resp.
        // at the bottom of each group)
        this.addCreateLine = params.addCreateLine;
        this.addCreateLineInGroups = params.addCreateLineInGroups;

        // Controls allow overriding "add a line" by custom controls.

        // Each <control> (only one is actually needed) is a container for (multiple) <create>.
        // Each <create> will be a "add a line" button with custom text and context.

        // The following code will browse the arch to find
        // all the <create> that are inside <control>

        if (this.addCreateLine) {
            this.creates = [];

            _.each(this.arch.children, function (child) {
                if (child.tag !== 'control') {
                    return;
                }

                _.each(child.children, function (child) {
                    if (child.tag !== 'create' || child.attrs.invisible) {
                        return;
                    }

                    self.creates.push({
                        context: child.attrs.context,
                        string: child.attrs.string,
                    });
                });
            });

            // Add the default button if we didn't find any custom button.
            if (this.creates.length === 0) {
                this.creates.push({
                    string: _t("Add a line"),
                });
            }
        }

        // if addTrashIcon is true, there will be a small trash icon at the end
        // of each line, so the user can delete a record.
        this.addTrashIcon = params.addTrashIcon;

        // replace the trash icon by X in case of many2many relations
        // so that it means 'unlink' instead of 'remove'
        this.isMany2Many = params.isMany2Many;

        this.currentRow = null;
        this.currentFieldIndex = null;
        this.allRecordsIds = null; // flat array of records ids used by navigation
    },
    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        if (this.editable) {
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
     * If the given recordID is a record in the list, toggle a className on its
     * row's cells for invalid fields, so that we can style those cells
     * differently.
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
        var fieldNames = this._super(recordID);
        this.$('.o_selected_row .o_data_cell').removeClass('o_invalid_cell');
        this.$('.o_selected_row .o_data_cell:has(> .o_field_invalid)').addClass('o_invalid_cell');
        return fieldNames;
    },
    /**
     * We need to override the confirmChange method from BasicRenderer to
     * reevaluate the row decorations.  Since they depends on the current value
     * of the row, they might have changed between each edit.
     *
     * @override
     */
    confirmChange: function (state, recordID) {
        var self = this;
        return this._super.apply(this, arguments).then(function (widgets) {
            if (widgets.length) {
                var $row = self._getRow(recordID);
                var record = self._getRecord(recordID);
                self._setDecorationClasses(record, $row);
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
     * @returns {Promise<AbstractField[]>} resolved with the list of widgets
     *                                      that have been reset
     */
    confirmUpdate: function (state, id, fields, ev) {
        var self = this;

        var oldData = this.state.data;
        this.state = state;
        return this.confirmChange(state, id, fields, ev).then(function () {
            // If no record with 'id' can be found in the state, the
            // confirmChange method will have rerendered the whole view already,
            // so no further work is necessary.
            var record = self._getRecord(id);
            if (!record) {
                return;
            }

            _.each(oldData, function (rec) {
                if (rec.id !== id) {
                    self._destroyFieldWidgets(rec.id);
                }
            });

            // re-render whole body (outside the dom)
            self.defs = [];
            var $newBody = self._renderBody();
            var defs = self.defs;
            delete self.defs;

            return Promise.all(defs).then(function () {
                // update registered modifiers to edit 'mode' because the call to
                // _renderBody set baseModeByRecord as 'readonly'
                _.each(self.columns, function (node) {
                    self._registerModifiers(node, record, null, {mode: 'edit'});
                });

                // store the selection range to restore it once the table will
                // be re-rendered, and the current cell re-selected
                var currentRowID, currentWidget, focusedElement, selectionRange;
                if (self.currentRow !== null) {
                    currentRowID = self._getRecordID(self.currentRow);
                    currentWidget = self.allFieldWidgets[currentRowID][self.currentFieldIndex];
                    if (currentWidget) {
                        focusedElement = currentWidget.getFocusableElement().get(0);
                        if (currentWidget.formatType !== 'boolean') {
                            selectionRange = dom.getSelectionRange(focusedElement);
                        }
                    }
                }

                // remove all rows except the one being edited, and insert rows
                // of the re-rendered body before and after it
                var $editedRow = self._getRow(id);
                $editedRow.nextAll().remove();
                $editedRow.prevAll().remove();
                var $newRow = $newBody.find('.o_data_row[data-id="' + id + '"]');
                var $tbody = self.$('tbody');
                $newRow.prevAll().each(function (i, prevRow) {
                    $tbody.prepend($(prevRow));
                });
                $newRow.nextAll().each(function (i, nextRow) {
                    $tbody.append($(nextRow));
                });

                if (self.currentRow !== null) {
                    var newRowIndex = $editedRow.prop('rowIndex') - 1;
                    self.currentRow = newRowIndex;
                    return self._selectCell(newRowIndex, self.currentFieldIndex, {force: true})
                        .then(function () {
                            // restore the selection range
                            currentWidget = self.allFieldWidgets[currentRowID][self.currentFieldIndex];
                            if (currentWidget) {
                                focusedElement = currentWidget.getFocusableElement().get(0);
                                if (selectionRange) {
                                    dom.setSelectionRange(focusedElement, selectionRange);
                                }
                            }
                        });
                }
            });
        });
    },
    /**
     * Edit the first record in the list
     */
    editFirstRecord: function () {
        this._selectCell(this._getFirstDataRowIndex(), 0);
    },
    /**
     * Edit a given record in the list
     *
     * @param {string} recordID
     */
    editRecord: function (recordID) {
        var $row = this._getRow(recordID);
        var rowIndex = $row.prop('rowIndex') - 1;
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
            return this._getRecordID(this.currentRow);
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
        this.state = state;
        var $row = this._getRow(recordID);
        if ($row.length === 0) {
            return;
        }
        if ($row.prop('rowIndex') - 1 === this.currentRow) {
            this.currentRow = null;
        }

        // destroy widgets first
        this._destroyFieldWidgets(recordID);
        // remove the row
        if (this.state.count >= 4) {
            $row.remove();
        } else {
            $row.replaceWith(this._renderEmptyRow());
        }
    },
    /**
     * Updates the already rendered row associated to the given recordID so that
     * it fits the given mode.
     *
     * @param {string} recordID
     * @param {string} mode
     * @returns {Promise}
     */
    setRowMode: function (recordID, mode) {
        var self = this;
        var record = self._getRecord(recordID);
        if (!record) {
            return Promise.resolve();
        }

        var editMode = (mode === 'edit');
        var $row = this._getRow(recordID);
        this.currentRow = editMode ? $row.prop('rowIndex') - 1 : null;
        var $tds = $row.children('.o_data_cell');
        var oldWidgets = _.clone(this.allFieldWidgets[record.id]);

        // When switching to edit mode, force the dimensions of all cells to
        // their current value so that they won't change if their content
        // changes, to prevent the view from flickering.
        // We need to use getBoundingClientRect instead of outerWidth to
        // prevent a rounding issue on Firefox.
        if (editMode) {
            $tds.each(function () {
                var $td = $(this);
                $td.css({width: $td[0].getBoundingClientRect().width});
            });
        }

        // Prepare options for cell rendering (this depends on the mode)
        var options = {
            renderInvisible: editMode,
            renderWidgets: editMode,
        };
        options.mode = editMode ? 'edit' : 'readonly';

        // Switch each cell to the new mode; note: the '_renderBodyCell'
        // function might fill the 'this.defs' variables with multiple promise
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
        $row.find('.o_list_record_selector input').prop('disabled', !record.res_id);

        return Promise.all(defs).then(function () {
            // necessary to trigger resize on fieldtexts
            core.bus.trigger('DOM_updated');
        });
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
     * @returns {Promise} The promise resolves if the row was unselected (and
     *   possibly removed). If may be rejected, when the row is dirty and the
     *   user refuses to discard its changes.
     */
    unselectRow: function () {
        var self = this;
        // Protect against calling this method when no row is selected
        if (this.currentRow === null) {
            return Promise.resolve();
        }
        var recordID = this._getRecordID(this.currentRow);
        var recordWidgets = this.allFieldWidgets[recordID];
        toggleWidgets(true);

        var prom = new Promise(function (resolve, reject) {
            self.trigger_up('save_line', {
                recordID: recordID,
                onSuccess: resolve,
                onFailure: reject,
            });
        });
        prom.guardedCatch(function() {
            toggleWidgets(false);
        });
        return prom;

        function toggleWidgets(disabled) {
            _.each(recordWidgets, function (widget) {
                var $el = widget.getFocusableElement();
                $el.prop('disabled', disabled);
            });
        }
    },
    /**
     * @override
     */
    updateState: function (state, params) {
        if (params.noRender) {
            // the state changed, but we won't do a re-rendering right now, so
            // remove computed modifiers data (as they are obsolete) to force
            // them to be recomputed at next (sub-)rendering
            this.allModifiersData = [];
        }
        return this._super.apply(this, arguments);
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
     * Returns the relative width according to the widget or the field type.
     * @see _renderHeader
     *
     * @param {Object} column a `field` arch node
     */
    _getColumnWidthFactor: function (column) {
        if (column.attrs.width) {
            // the width attribute has precedence on the width factor
            return 0;
        }
        var fieldType = this.state.fields[column.attrs.name].type;
        var widget = this.state.fieldsInfo.list[column.attrs.name].Widget.prototype;
        if ('widthFactor' in widget) {
            return widget.widthFactor;
        }
        switch (fieldType) {
            case 'binary': return 1;
            case 'boolean': return 0.4;
            case 'char': return 1;
            case 'date': return 1;
            case 'datetime': return 1.5;
            case 'float': return 1;
            case 'html': return 3;
            case 'integer': return 0.8;
            case 'many2many': return 2.2;
            case 'many2one': return 1.5;
            case 'monetary': return 1.2;
            case 'one2many': return 2.2;
            case 'reference': return 1.5;
            case 'selection': return 1.5;
            case 'text': return 3;
            default: return 1;
        }
    },
    /**
     *
     * @returns {integer}
     */
    _getFirstDataRowIndex: function () {
        return this.$('.o_data_row:first').prop('rowIndex') - 1;
    },
    /**
     * Given a table row inside a group, returns the index of the first data
     * row of the next group (if any).
     *
     * @param {jQuery} $row this row must be inside a group
     * @returns {integer|null}
     */
    _getNextGroupFirstRowIndex: function ($row) {
        var $nextBody = $row.closest('tbody').next();
        while ($nextBody.length && !$nextBody.find('.o_data_row').length) {
            $nextBody = $nextBody.next();
        }
        if ($nextBody.find('.o_data_row').length) {
            return $nextBody.find('.o_data_row:first').prop('rowIndex') - 1;
        }
        return null;
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
     * Traverse this.state to find and return the record with given dataPoint id
     * (for grouped list views, the record could be deep down in state tree).
     *
     * @override
     * @private
     */
    _getRecord: function (recordId) {
        var record;
        utils.traverse_records(this.state, function (r) {
            if (r.id === recordId) {
                record = r;
            }
        });
        return record;
    },
    /**
     * Retrieve the record dataPoint id from a rowIndex as the row DOM element
     * stores the record id in data.
     *
     * @private
     * @param {integer} rowIndex
     * @returns {string} record dataPoint id
     */
    _getRecordID: function (rowIndex) {
        var $tr = this.$('table.o_list_view > tbody tr').eq(rowIndex);
        return $tr.data('id');
    },
    /**
     * Return the jQuery tr element corresponding to the given record dataPoint
     * id.
     *
     * @private
     * @param {string} [recordId]
     * @returns {jQueryElement}
     */
    _getRow: function (recordId) {
        return this.$('.o_data_row[data-id="' + recordId + '"]');
    },
    /**
     * Move the cursor on the end of the previous line (or of the last line if
     * we are on the first one).
     *
     * @private
     */
    _moveToPreviousLine: function () {
        var self = this;
        if (!this.allRecordsIds) {
            // compute the flat array of all records ids only once
            this.allRecordIds = [];
            utils.traverse_records(this.state, function (data) {
                self.allRecordIds.push(data.id);
            });
        }
        var curRecordId = this._getRecordID(this.currentRow);
        var curRecordIndex = this.allRecordIds.indexOf(curRecordId);
        var prevRecordIndex = curRecordIndex === 0 ? this.allRecordIds.length - 1 : curRecordIndex - 1;
        this.commitChanges(curRecordId).then(function () {
            var $prevRow = self._getRow(self.allRecordIds[prevRecordIndex]);
            var prevRowIndex = $prevRow.prop('rowIndex') - 1;
            self._selectCell(prevRowIndex, self.columns.length - 1, {inc: -1});
        });
    },
    /**
     * Move the cursor on the beginning of the next line, if possible.
     * If we are on the last line (of a group in the grouped case) and the list
     * is editable="bottom", we create a new record, otherwise, we move the
     * cursor to the first line (of the next group in the grouped case).
     *
     * @private
     * @param {Object} [options]
     * @param {boolean} [options.forceCreate=false] typically set to true when
     *   navigating with ENTER ; in this case, if the next row is the 'Add a
     *   line' row, always create a new record (never skip it, like TAB does
     *   under some conditions)
     */
    _moveToNextLine: function (options) {
        var self = this;
        options = options || {};
        var recordID = this._getRecordID(this.currentRow);
        var record = this._getRecord(recordID);

        this.commitChanges(recordID).then(function () {
            var fieldNames = self.canBeSaved(recordID);
            if (fieldNames.length && (record.isDirty() || options.forceCreate)) {
                // the current row is invalid, we only leave it if it is not dirty
                // (we didn't make any change on this row, which is a new one) and
                // we are navigating with TAB (forceCreate=false)
                return;
            }

            // compute the index of the next (record) row to select, if any
            var nextRowIndex = null;
            var groupId;
            if (!self.isGrouped) {
                // ungrouped case
                if (self.currentRow < self.state.data.length - 1) {
                    nextRowIndex = self.currentRow + 1;
                } else if (!options.forceCreate && !record.isDirty()) {
                    self.trigger_up('discard_changes', {
                        recordID: recordID,
                        onSuccess: function () {
                            self.trigger_up('activate_next_widget');
                        },
                    });
                    return;
                }
            } else {
                // grouped case
                var $currentRow = self._getRow(recordID);
                var $nextRow = $currentRow.next();
                if ($nextRow.hasClass('o_data_row')) {
                    // the next row is a record row (in same group), select it
                    nextRowIndex = self.currentRow + 1;
                } else if ($nextRow.hasClass('o_add_record_row') && self.editable === "bottom") {
                    // the next row is the 'Add a line' row (i.e. the current one is the last record
                    // row of the group)
                    if (options.forceCreate || record.isDirty()) {
                        // if we modified the current record, add a row to create a new record
                        groupId = $nextRow.data('group-id');
                    } else {
                        // if we didn't change anything to the current line (e.g. we pressed TAB on
                        // each cell without modifying/entering any data), we discard that line (if
                        // it was a new one) and move to the first record of the next group
                        nextRowIndex = self._getNextGroupFirstRowIndex($currentRow);
                        self.trigger_up('discard_changes', {
                            recordID: recordID,
                            onSuccess: function () {
                                if (nextRowIndex !== null) {
                                    if (!record.res_id) {
                                        // the current record was a new one, so we decrement
                                        // nextRowIndex as that row has been removed meanwhile
                                        nextRowIndex--;
                                    }
                                    self._selectCell(nextRowIndex, 0);
                                } else {
                                    // we were in the last group, so go back to the top
                                    self._selectCell(self._getFirstDataRowIndex(), 0, {});
                                }
                            },
                        });
                        return;
                    }
                } else {
                    // there is no 'Add a line' row (i.e. the create feature is disabled), or the
                    // list is editable="top", we focus the first record of the next group if any
                    nextRowIndex = self._getNextGroupFirstRowIndex($currentRow);
                    if (nextRowIndex === null) {
                        // we were on the last group, so we go back to the top of the list
                        nextRowIndex = self._getFirstDataRowIndex();
                    }
                }
            }

            // if there is a (record) row to select, select it, otherwise, add a new record (in the
            // correct group, if the view is grouped)
            if (nextRowIndex !== null) {
                self._selectCell(nextRowIndex, 0);
            } else {
                self.unselectRow().then(function () {
                    // if for some reason (e.g. create feature is disabled) we can't add a new
                    // record, select the first record row
                    self.trigger_up('add_record', {
                        groupId: groupId,
                        onFail: self._selectCell.bind(self, self._getFirstDataRowIndex(), 0, {}),
                    });
                });
            }
        });
    },
    /**
     * Overridden to set weights on columns for the fixed layout.
     *
     * @override
     * @private
     */
    _processColumns: function () {
        this._super.apply(this, arguments);

        if (this.editable) {
            var self = this;
            this.columns.forEach(function (column) {
                if (column.attrs.width_factor) {
                    column.attrs.widthFactor = parseFloat(column.attrs.width_factor, 10);
                } else {
                    if (column.tag === 'field') {
                        column.attrs.widthFactor = self._getColumnWidthFactor(column);
                    } else {
                        column.attrs.widthFactor = 1;
                    }
                }
            });
        }
    },
    /**
     * @override
     * @returns {Promise}
     */
    _render: function () {
        this.currentRow = null;
        this.currentFieldIndex = null;
        return this._super.apply(this, arguments);
    },
    /**
     * Override to add the 'Add an item' link to the end of last-level opened
     * groups.
     *
     * @override
     * @private
     */
    _renderGroup: function (group) {
        var result = this._super.apply(this, arguments);
        if (!group.groupedBy.length && this.addCreateLineInGroups) {
            var $groupBody = result[0];
            var $a = $('<a href="#" role="button">')
                .text(_t("Add a line"))
                .attr('data-group-id', group.id);
            var $td = $('<td>')
                        .attr('colspan', this._getNumberOfCols())
                        .addClass('o_group_field_row_add')
                        .attr('tabindex', -1)
                        .append($a);
            var $tr = $('<tr>', {class: 'o_add_record_row'})
                        .attr('data-group-id', group.id)
                        .append($td);
            $groupBody.append($tr.prepend($('<td>').html('&nbsp;')));
        }
        return result;
    },
    /**
     * The renderer needs to support reordering lines.  This is only active in
     * edit mode. The handleField attribute is set when there is a sequence
     * widget.
     *
     * @override
     */
    _renderBody: function () {
        var self = this;
        var $body = this._super.apply(this, arguments);
        if (this.hasHandle) {
            $body.sortable({
                axis: 'y',
                items: '> tr.o_data_row',
                helper: 'clone',
                handle: '.o_row_handle',
                stop: function (event, ui) {
                    self.unselectRow().then(function () {
                        self._moveRecord(ui.item.data('id'), ui.item.index());
                    });
                },
            });
        }
        return $body;
    },
    /**
     * Override to optionally add a th in the header for the remove icon column.
     *
     * @override
     * @private
     */
    _renderHeader: function () {
        var $thead = this._super.apply(this, arguments);

        if (this.editable) {
            var totalWidth = this.columns.reduce(function (acc, column) {
                return acc + column.attrs.widthFactor;
            }, 0);
            this.columns.forEach(function (column) {
                var $cell = $thead.find('th[data-name=' + column.attrs.name + ']');
                if (column.attrs.width) {
                    $cell.css('width', column.attrs.width);
                } else if (column.attrs.widthFactor) {
                    $cell.css('width', (column.attrs.widthFactor / totalWidth * 100) + '%');
                }
            });
        }

        if (this.addTrashIcon) {
            $thead.find('tr').append($('<th>', {class: 'o_list_record_remove_header'}));
        }
        return $thead;
    },
    /**
     * Editable rows are possibly extended with a trash icon on their right, to
     * allow deleting the corresponding record.
     * For many2many editable lists, the trash bin is replaced by X.
     *
     * @override
     * @param {any} record
     * @param {any} index
     * @returns {jQueryElement}
     */
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);
        if (this.addTrashIcon) {
            var $icon = this.isMany2Many ?
                            $('<button>', {class: 'fa fa-times', name: 'unlink', 'aria-label': _t('Unlink row ') + (index+1)}) :
                            $('<button>', {class: 'fa fa-trash-o', name: 'delete', 'aria-label': _t('Delete row ') + (index+1)});
            var $td = $('<td>', {class: 'o_list_record_remove'}).append($icon);
            $row.append($td);
        }
        return $row;
    },
    /**
     * If the editable list view has the parameter addCreateLine, we need to
     * add a last row with the necessary control.
     *
     * If the list has a handleField, we want to left-align the first button
     * on the first real column.
     *
     * @override
     * @returns {jQueryElement[]}
     */
    _renderRows: function () {
        var $rows = this._super();
        if (this.addCreateLine) {
            var $tr = $('<tr>');
            var colspan = this._getNumberOfCols();

            if (this.handleField) {
                colspan = colspan - 1;
                $tr.append('<td>');
            }

            var $td = $('<td>')
                .attr('colspan', colspan)
                .addClass('o_field_x2many_list_row_add');
            $tr.append($td);
            $rows.push($tr);

            _.each(this.creates, function (create, index) {
                var $a = $('<a href="#" role="button">')
                    .attr('data-context', create.context)
                    .text(create.string);
                if (index > 0) {
                    $a.addClass('ml16');
                }
                $td.append($a);
            });
        }
        return $rows;
    },
    /**
     * @override
     * @private
     * @returns {Promise} this promise is resolved immediately
     */
    _renderView: function () {
        var self = this;
        this.currentRow = null;
        this.allRecordsIds = null;
        return this._super.apply(this, arguments).then(function () {
            if (self.editable) {
                self.$('table').addClass('o_editable_list');
            }
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
     * @param {integer} [options.inc=1] the increment to use when searching for
     *   the "next" possible cell (if the cell to select can't be selected)
     * @return {Promise} fails if no cell could be selected
     */
    _selectCell: function (rowIndex, fieldIndex, options) {
        options = options || {};
        // Do nothing if the user tries to select current cell
        if (!options.force && rowIndex === this.currentRow && fieldIndex === this.currentFieldIndex) {
            return Promise.resolve();
        }
        var wrap = options.wrap === undefined ? true : options.wrap;

        // Select the row then activate the widget in the correct cell
        var self = this;
        return this._selectRow(rowIndex).then(function () {
            var recordID = self._getRecordID(rowIndex);
            var record = self._getRecord(recordID);
            if (fieldIndex >= (self.allFieldWidgets[record.id] || []).length) {
                return Promise.reject();
            }
            // _activateFieldWidget might trigger an onchange,
            // which requires currentFieldIndex to be set
            // so that the cursor can be restored
            var oldFieldIndex = self.currentFieldIndex;
            self.currentFieldIndex = fieldIndex;
            fieldIndex = self._activateFieldWidget(record, fieldIndex, {
                inc: options.inc || 1,
                wrap: wrap,
                event: options && options.event,
            });
            if (fieldIndex < 0) {
                self.currentFieldIndex = oldFieldIndex;
                return Promise.reject();
            }
            self.currentFieldIndex = fieldIndex;
        });
    },
    /**
     * Activates the row at the given row index.
     *
     * @param {integer} rowIndex
     * @returns {Promise}
     */
    _selectRow: function (rowIndex) {
        // Do nothing if already selected
        if (rowIndex === this.currentRow) {
            return Promise.resolve();
        }
        var recordId = this._getRecordID(rowIndex);
        // To select a row, the currently selected one must be unselected first
        var self = this;
        return this.unselectRow().then(function () {
            if (!recordId) {
                // The row to selected doesn't exist anymore (probably because
                // an onchange triggered when unselecting the previous one
                // removes rows)
                return Promise.reject();
            }
            // Notify the controller we want to make a record editable
            return new Promise(function (resolve) {
                self.trigger_up('edit_line', {
                    recordId: recordId,
                    onSuccess: resolve,
                });
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * This method is called when we click on the 'Add a line' button in a groupby
     * list view.
     *
     * @param {MouseEvent} ev
     */
    _onAddRecordToGroup: function (ev) {
        ev.preventDefault();
        // we don't want the click to cause other effects, such as unselecting
        // the row that we are creating, because it counts as a click on a tr
        ev.stopPropagation();

        var self = this;
        var groupId = $(ev.target).data('group-id');
        this.currentGroupId = groupId;
        this.unselectRow().then(function () {
            self.trigger_up('add_record', {
                groupId: groupId,
            });
        });
    },
    /**
     * This method is called when we click on the 'Add a line' button in a sub
     * list such as a one2many in a form view.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onAddRecord: function (ev) {
        // we don't want the browser to navigate to a the # url
        ev.preventDefault();

        // we don't want the click to cause other effects, such as unselecting
        // the row that we are creating, because it counts as a click on a tr
        ev.stopPropagation();

        // but we do want to unselect current row
        var self = this;
        this.unselectRow().then(function () {
            self.trigger_up('add_record', {context: ev.currentTarget.dataset.context && [ev.currentTarget.dataset.context]}); // TODO write a test, the promise was not considered
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
        if (!this.editable || $(event.target).prop('special_click')) {
            return;
        }
        var $td = $(event.currentTarget);
        var $tr = $td.parent();
        var rowIndex = $tr.prop('rowIndex') - 1;
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
     * Manages the keyboard events on the list. If the list is not editable, when the user navigates to
     * a cell using the keyboard, if he presses enter, enter the model represented by the line
     *
     * @private
     * @param {KeyboardEvent} ev
     * @override
     */
    _onKeyDown: function (ev) {
        var $target = $(ev.currentTarget);
        var $tr = $target.closest('tr');

        if (this.editable && ev.keyCode === $.ui.keyCode.ENTER && $tr.hasClass('o_selected_row')) {
            // enter on a textarea for example, let it bubble
            return;
        }

        if (this.editable && ev.keyCode === $.ui.keyCode.ENTER && !$tr.hasClass('o_selected_row') && !$tr.hasClass('o_group_header')) {
            ev.stopPropagation();
            ev.preventDefault();
            if ($target.closest('td').hasClass('o_group_field_row_add')) {
                this._onAddRecordToGroup(ev);
            } else {
                this._onCellClick(ev);
            }
        } else {
            this._super.apply(this, arguments);
        }
    },
    /**
     * @private
     * @param {KeyDownEvent} e
     */
    _onKeyDownAddRecord: function (e) {
        switch(e.keyCode) {
            case $.ui.keyCode.ENTER:
                e.stopPropagation();
                e.preventDefault();
                this._onAddRecord(e);
                break;
        }
    },
    /**
     * It will returns the last visible widget that is editable
     *
     * @private
     * @returns {Class} Widget returns last widget
     */
    _getLastWidget: function () {
        var recordID = this._getRecordID(this.currentRow);
        var recordWidgets = this.allFieldWidgets[recordID];
        var lastWidget = _.chain(recordWidgets).filter(function (widget) {
            var isLast =
                widget.$el.is(':visible') &&
                (
                    widget.$('input').length > 0 || widget.tagName === 'input' ||
                    widget.$('textarea').length > 0 || widget.tagName === 'textarea'
                ) &&
                !widget.$el.hasClass('o_readonly_modifier');
            return isLast;
        }).last().value();
        return lastWidget;
    },
    /**
     * Handles the keyboard navigation according to events triggered by field
     * widgets.
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
        var self = this;
        ev.stopPropagation(); // stop the event, the action is done by this renderer
        switch (ev.data.direction) {
            case 'previous':
                if (this.currentFieldIndex > 0) {
                    this._selectCell(this.currentRow, this.currentFieldIndex - 1, {inc: -1, wrap: false})
                        .guardedCatch(this._moveToPreviousLine.bind(this));
                } else {
                    this._moveToPreviousLine();
                }
                break;
            case 'next':
                var column = this.columns[this.currentFieldIndex];
                var lastWidget = this._getLastWidget();
                if (column.attrs.name === lastWidget.name) {
                    this._moveToNextLine();
                } else {
                    if (this.currentFieldIndex + 1 < this.columns.length) {
                        this._selectCell(this.currentRow, this.currentFieldIndex + 1, {wrap: false})
                            .guardedCatch(this._moveToNextLine.bind(this));
                    } else {
                        this._moveToNextLine();
                    }
                 }
                break;
            case 'next_line':
                this._moveToNextLine({forceCreate: true});
                break;
            case 'cancel':
                // stop the original event (typically an ESCAPE keydown), to
                // prevent from closing the potential dialog containing this list
                // also auto-focus the 1st control, if any.
                ev.data.originalEvent.stopPropagation();
                var rowIndex = this.currentRow;
                var cellIndex = this.currentFieldIndex + 1;
                this.trigger_up('discard_changes', {
                    recordID: ev.target.dataPointID,
                    onSuccess: function () {
                        var recordId = self._getRecordID(rowIndex);
                        if (recordId) {
                            var correspondingRow = self._getRow(recordId);
                            correspondingRow.children().eq(cellIndex).focus();
                        } else if (self.currentGroupId) {
                                self.$('a[data-group-id=' + self.currentGroupId + ']').focus();
                        } else {
                            self.$('.o_field_x2many_list_row_add a:first').focus(); // FIXME
                        }
                    }
                });
                break;
        }
    },
    /**
     * Triggers a remove event. I don't know why we stop the propagation of the
     * event.
     *
     * @param {MouseEvent} event
     */
    _onRemoveIconClick: function (event) {
        event.stopPropagation();
        var $row = $(event.target).closest('tr');
        var id = $row.data('id');
        if ($row.hasClass('o_selected_row')) {
            this.trigger_up('list_record_remove', {id: id});
        } else {
            var self = this;
            this.unselectRow().then(function () {
                self.trigger_up('list_record_remove', {id: id});
            });
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
        if (!this.editable) {
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
