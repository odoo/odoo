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
    RESIZE_DELAY: 200,
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
     * @param {boolean} params.isMultiEditable
     */
    init: function (parent, state, params) {
        var self = this;
        this._super.apply(this, arguments);

        this.editable = params.editable;
        this.isMultiEditable = params.isMultiEditable;
        this.columnWidths = false;

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
        this.isResizing = false;
        this.eventListeners = [];
    },
    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        core.bus.on('click', this, this._onWindowClicked.bind(this));
        core.bus.on('resize', this, _.debounce(this._onResize.bind(this), this.RESIZE_DELAY));
        core.bus.on('DOM_updated', this, () => this._freezeColumnWidths());
        return this._super();
    },
    /**
     * Overriden to unbind all attached listeners
     *
     * @override
     */
    destroy: function () {
        this.eventListeners.forEach(listener => {
            const { type, el, callback, options } = listener;
            el.removeEventListener(type, callback, options);
        });
        return this._super.apply(this, arguments);
    },
    /**
     * The list renderer needs to know if it is in the DOM, and to be notified
     * when it is attached to the DOM to properly compute column widths.
     *
     * @override
     */
    on_attach_callback: function () {
        this.isInDOM = true;
        this._freezeColumnWidths();
        this._super();
    },
    /**
     * The list renderer needs to know if it is in the DOM to properly compute
     * column widths.
     *
     * @override
     */
    on_detach_callback: function () {
        this.isInDOM = false;
        this._super();
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
     * in a normal list view).
     *
     * The update is more difficult when other rows could have been changed. We
     * need to potentially remove some lines, add some other lines, update some
     * other lines and maybe reorder a few of them.  This problem would neatly
     * be solved by using a virtual dom, but we do not have this luxury yet.
     * So, in the meantime, what we do is basically remove every current row
     * except the 'main' one (the row which caused the update), then rerender
     * every new row and add them before/after the main one.
     *
     * Note that this function assumes that the list isn't grouped, which is
     * fine as it's never the case for x2many lists.
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
                var currentRowID;
                var currentWidget;
                var focusedElement;
                var selectionRange;
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

                // remove all data rows except the one being edited, and insert
                // data rows of the re-rendered body before and after it
                var $editedRow = self._getRow(id);
                $editedRow.nextAll('.o_data_row').remove();
                $editedRow.prevAll('.o_data_row').remove();
                var $newRow = $newBody.find('.o_data_row[data-id="' + id + '"]');
                $newRow.prevAll('.o_data_row').get().reverse().forEach(function (row) {
                    $(row).insertBefore($editedRow);
                });
                $newRow.nextAll('.o_data_row').get().reverse().forEach(function (row) {
                    $(row).insertAfter($editedRow);
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
    editFirstRecord: function (ev) {
        const $borderRow = this._getBorderRow(ev.data.side || 'first');
        this._selectCell($borderRow.prop('rowIndex') - 1, ev.data.cellIndex || 0);
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
     * Gives focus to a specific cell, given its row and its related column.
     *
     * @param {string} recordId
     * @param {Object} column
     */
    focusCell: function (recordId, column) {
        var $row = this._getRow(recordId);
        var cellIndex = this.columns.indexOf(column);
        $row.find('.o_data_cell')[cellIndex].focus();
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
     * Returns whether the list is in multiple record edition from a given record.
     *
     * @private
     * @param {string} recordId
     * @returns {boolean}
     */
    isInMultipleRecordEdition: function (recordId) {
        return this.isEditable() && this.isMultiEditable && this.selection.includes(recordId);
    },
    /**
     * Returns whether the list can be edited.
     * It's true when:
     * - the list `editable` property is set,
     * - or at least one record is selected (becomes partially editable)
     *
     * @returns {boolean}
     */
    isEditable: function () {
        return this.editable || (this.isMultiEditable && this.selection.length);
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
            this._enableRecordSelectors();
        }

        // destroy widgets first
        this._destroyFieldWidgets(recordID);
        // remove the row
        if (this.state.count >= 4) {
            $row.remove();
        } else {
            // we want to always keep at least 4 (possibly empty) rows
            var $emptyRow = this._renderEmptyRow();
            $row.replaceWith($emptyRow);
            // move the empty row we just inserted after last data row
            const $lastDataRow = this.$('.o_data_row:last');
            if ($lastDataRow.length) {
                $emptyRow.insertAfter($lastDataRow);
            }
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
        if (editMode) {
            this._disableRecordSelectors();
        } else {
            this._enableRecordSelectors();
        }

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
        // Protect against calling this method when no row is selected
        if (this.currentRow === null) {
            return Promise.resolve();
        }
        var recordID = this._getRecordID(this.currentRow);
        var recordWidgets = this.allFieldWidgets[recordID];
        function toggleWidgets(disabled) {
            _.each(recordWidgets, function (widget) {
                var $el = widget.getFocusableElement();
                $el.prop('disabled', disabled);
            });
        }

        toggleWidgets(true);
        return new Promise((resolve, reject) => {
            this.trigger_up('save_line', {
                recordID: recordID,
                onSuccess: resolve,
                onFailure: reject,
            });
        }).then(changedFields => {
            this._enableRecordSelectors();
            // If any field has changed and if the list is in multiple edition,
            // we send a truthy boolean to _selectRow to tell it not to select
            // the following record.
            return changedFields && changedFields.length && this.isInMultipleRecordEdition(recordID);
        }).guardedCatch(() => {
            toggleWidgets(false);
        });
    },
    /**
     * @override
     */
    updateState: function (state, params) {
        // There are some cases where a record is added to an invisible list
        // e.g. set a quotation template with optionnal products
        if (params.keepWidths && this.$el.is(':visible')) {
            this._storeColumnWidths();
        }
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
     * Used to bind event listeners so that they can be unbound when the list
     * is destroyed.
     * There is no reverse method (list._removeEventListener) because there is
     * no issue with removing an non-existing listener.
     *
     * @private
     * @param {string} type event name
     * @param {EventTarget} el event target
     * @param {Function} callback callback function to attach
     * @param {Object} options event listener options
     */
    _addEventListener: function (type, el, callback, options) {
        el.addEventListener(type, callback, options);
        this.eventListeners.push({ type, el, callback, options });
    },
    /**
     * Handles the assignation of default widths for each column header.
     * If the list is empty, an arbitrary absolute or relative width will be
     * given to the header
     *
     * @see _getColumnWidth for detailed information about which width is
     * given to a certain field type.
     *
     * @private
     */
    _computeDefaultWidths: function () {
        const isListEmpty = !this._hasVisibleRecords(this.state);
        const relativeWidths = [];
        this.columns.forEach(column => {
            const th = this._getColumnHeader(column);
            if (th.offsetParent === null) {
                relativeWidths.push(false);
            } else {
                const width = this._getColumnWidth(column);
                if (width.match(/[a-zA-Z]/)) { // absolute width with measure unit (e.g. 100px)
                    if (isListEmpty) {
                        th.style.width = width;
                    } else {
                        // If there are records, we force a min-width for fields with an absolute
                        // width to ensure a correct rendering in edition
                        th.style.minWidth = width;
                    }
                    relativeWidths.push(false);
                } else { // relative width expressed as a weight (e.g. 1.5)
                    relativeWidths.push(parseFloat(width, 10));
                }
            }
        });

        // Assignation of relative widths
        if (isListEmpty) {
            const totalWidth = this._getColumnsTotalWidth(relativeWidths);
            for (let i in this.columns) {
                if (relativeWidths[i]) {
                    const th = this._getColumnHeader(this.columns[i]);
                    th.style.width = (relativeWidths[i] / totalWidth * 100) + '%';
                }
            }
            // Manualy assigns trash icon header width since it's not in the columns
            const trashHeader = this.el.getElementsByClassName('o_list_record_remove_header')[0];
            if (trashHeader) {
                trashHeader.style.width = '32px';
            }
        }
    },
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
     * When editing a row, we want to disable all record selectors.
     *
     * @private
     */
    _disableRecordSelectors: function () {
        this.$('.o_list_record_selector input').attr('disabled', 'disabled');
    },
    /**
     * @private
     */
    _enableRecordSelectors: function () {
        this.$('.o_list_record_selector input').attr('disabled', false);
    },
    /**
     * This function freezes the column widths and forces a fixed table-layout,
     * once the browser has computed the optimal width of each column according
     * to the displayed records. We want to freeze widths s.t. it doesn't
     * flicker when we switch a row in edition.
     *
     * We skip this when there is no record as we don't want to fix widths
     * according to column's labels. In this case, we fallback on the 'weight'
     * heuristic, which assigns to each column a fixed or relative width
     * depending on the widget or field type.
     *
     * Note that the list must be in the DOM when this function is called.
     *
     * @private
     */
    _freezeColumnWidths: function () {
        if (!this.columnWidths && this.el.offsetParent === null) {
            // there is no record nor widths to restore or the list is not visible
            // -> don't force column's widths w.r.t. their label
            return;
        }
        const thElements = [...this.el.querySelectorAll('table thead th')];
        if (!thElements.length) {
            return;
        }
        const table = this.el.getElementsByTagName('table')[0];
        let columnWidths = this.columnWidths;

        if (!columnWidths || !columnWidths.length) { // no column widths to restore
            // Set table layout auto and remove inline style to make sure that css
            // rules apply (e.g. fixed width of record selector)
            table.style.tableLayout = 'auto';
            thElements.forEach(th => {
                th.style.width = null;
                th.style.maxWidth = null;
            });

            // Resets the default widths computation now that the table is visible.
            this._computeDefaultWidths();

            // Squeeze the table by applying a max-width on largest columns to
            // ensure that it doesn't overflow
            columnWidths = this._squeezeTable();
        }

        thElements.forEach((th, index) => {
            // Width already set by default relative width computation
            if (!th.style.width) {
                th.style.width = `${columnWidths[index]}px`;
            }
        });

        // Set the table layout to fixed
        table.style.tableLayout = 'fixed';
    },
    /**
     * Returns the first or last editable row of the list
     *
     * @private
     * @returns {integer}
     */
    _getBorderRow: function (side) {
        let $borderDataRow = this.$(`.o_data_row:${side}`);
        if (!this._isRecordEditable($borderDataRow.data('id'))) {
            $borderDataRow = this._getNearestEditableRow($borderDataRow, side === 'first');
        }
        return $borderDataRow;
    },
    /**
     * Compute the sum of the weights for each column, given an array containing
     * all relative widths. param `$thead` is useful for studio, in order to
     * show column hooks.
     *
     * @private
     * @param {jQuery} $thead
     * @param {number[]} relativeWidths
     * @return {integer}
     */
    _getColumnsTotalWidth(relativeWidths) {
        return relativeWidths.reduce((acc, width) => acc + width, 0);
    },
    /**
     * Returns the width of a column according the 'width' attribute set in the
     * arch, the widget or the field type. A fixed width is harcoded for some
     * field types (e.g. date and numeric fields). By default, the remaining
     * space is evenly distributed between the other fields (with a factor '1').
     *
     * This is only used when there is no record in the list (i.e. when we can't
     * let the browser compute the optimal width of each column).
     *
     * @see _renderHeader
     * @private
     * @param {Object} column an arch node
     * @returns {string} either a weight factor (e.g. '1.5') or a css width
     *   description (e.g. '120px')
     */
    _getColumnWidth: function (column) {
        if (column.attrs.width) {
            return column.attrs.width;
        }
        const fieldsInfo = this.state.fieldsInfo.list;
        const name = column.attrs.name;
        if (!fieldsInfo[name]) {
            // Unnamed columns get default value
            return '1';
        }
        const widget = fieldsInfo[name].Widget.prototype;
        if ('widthInList' in widget) {
            return widget.widthInList;
        }
        const field = this.state.fields[name];
        if (!field) {
            // this is not a field. Probably a button or something of unknown
            // width.
            return '1';
        }
        const fixedWidths = {
            boolean: '50px',
            date: '92px',
            datetime: '146px',
            float: '92px',
            integer: '74px',
            monetary: '104px',
        };
        let type = field.type;
        if (fieldsInfo[name].widget in fixedWidths) {
            type = fieldsInfo[name].widget;
        }
        return fixedWidths[type] || '1';
    },
    /**
     * Gets the th element corresponding to a given column.
     *
     * @private
     * @param {Object} column
     * @returns {HTMLElement}
     */
    _getColumnHeader: function (column) {
        const { icon, name, string } = column.attrs;
        if (name) {
            return this.el.querySelector(`thead th[data-name="${name}"]`);
        } else if (string) {
            return this.el.querySelector(`thead th[data-string="${string}"]`);
        } else if (icon) {
            return this.el.querySelector(`thead th[data-icon="${icon}"]`);
        }
    },
    /**
     * Returns the nearest editable row starting from a given table row.
     * If the list is grouped, jumps to the next unfolded group
     *
     * @private
     * @param {jQuery} $row starting point
     * @param {boolean} next whether the requested row should be the next or the previous one
     * @return {jQuery|null}
     */
    _getNearestEditableRow: function ($row, next) {
        const direction = next ? 'next' : 'prev';
        let $nearestRow;
        if (this.editable) {
            $nearestRow = $row[direction]();
            if (!$nearestRow.hasClass('o_data_row')) {
                var $nextBody = $row.closest('tbody')[direction]();
                while ($nextBody.length && !$nextBody.find('.o_data_row').length) {
                    $nextBody = $nextBody[direction]();
                }
                $nearestRow = $nextBody.find(`.o_data_row:${next ? 'first' : 'last'}`);
            }
        } else {
            // In readonly lists, look directly into selected records
            const recordId = $row.data('id');
            const rowSelectionIndex = this.selection.indexOf(recordId);
            let nextRowIndex;
            if (rowSelectionIndex < 0) {
                nextRowIndex = next ? 0 : this.selection.length - 1;
            } else {
                nextRowIndex = rowSelectionIndex + (next ? 1 : -1);
            }
            // Index might be out of range, will then return an empty jQuery object
            $nearestRow = this._getRow(this.selection[nextRowIndex]);
        }
        return $nearestRow;
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
        var $tr = this.$('table.o_list_table > tbody tr').eq(rowIndex);
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
     * This function returns true iff records are visible in the list, i.e.
     *   if the list is ungrouped: true iff the list isn't empty;
     *   if the list is grouped: true iff there is at least one unfolded group
     *     containing records.
     *
     * @param {Object} list a datapoint
     * @returns {boolean}
     */
    _hasVisibleRecords: function (list) {
        if (!list.groupedBy.length) {
            return !!list.data.length;
        } else {
            var hasVisibleRecords = false;
            for (var i = 0; i < list.data.length; i++) {
                hasVisibleRecords = hasVisibleRecords || this._hasVisibleRecords(list.data[i]);
            }
            return hasVisibleRecords;
        }
    },
    /**
     * Returns whether a recordID is currently editable.
     *
     * @param {string} recordID
     * @returns {boolean}
     */
    _isRecordEditable: function (recordID) {
        return this.editable || (this.isMultiEditable && this.selection.includes(recordID));
    },
    /**
     * Moves to the next row in the list
     *
     * @private
     * @params {Object} [options] see @_moveToSideLine
     */
    _moveToNextLine: function (options) {
        this._moveToSideLine(true, options);
    },
    /**
     * Moves to the previous row in the list
     *
     * @private
     * @params {Object} [options] see @_moveToSideLine
     */
    _moveToPreviousLine: function (options) {
        this._moveToSideLine(false, options);
    },
    /**
     * Moves the focus to the nearest editable row before or after the current one.
     * If we arrive at the end of the list (or of a group in the grouped case) and the list
     * is editable="bottom", we create a new record, otherwise, we move the
     * cursor to the first row (of the next group in the grouped case).
     *
     * @private
     * @param {number} next whether to move to the next or previous row
     * @param {Object} [options]
     * @param {boolean} [options.forceCreate=false] typically set to true when
     *   navigating with ENTER ; in this case, if the next row is the 'Add a
     *   row' one, always create a new record (never skip it, like TAB does
     *   under some conditions)
     */
    _moveToSideLine: function (next, options) {
        options = options || {};
        const recordID = this._getRecordID(this.currentRow);
        this.commitChanges(recordID).then(() => {
            const record = this._getRecord(recordID);
            const multiEdit = this.isInMultipleRecordEdition(recordID);
            if (!multiEdit) {
                const fieldNames = this.canBeSaved(recordID);
                if (fieldNames.length && (record.isDirty() || options.forceCreate)) {
                    // the current row is invalid, we only leave it if it is not dirty
                    // (we didn't make any change on this row, which is a new one) and
                    // we are navigating with TAB (forceCreate=false)
                    return;
                }
            }
            // compute the index of the next (record) row to select, if any
            const side = next ? 'first' : 'last';
            const borderRowIndex = this._getBorderRow(side).prop('rowIndex') - 1;
            const cellIndex = next ? 0 : this.allFieldWidgets[recordID].length - 1;
            const cellOptions = { inc: next ? 1 : -1, force: true };
            const $currentRow = this._getRow(recordID);
            const $nextRow = this._getNearestEditableRow($currentRow, next);
            let nextRowIndex = null;
            let groupId;

            if (!this.isGrouped) {
                // ungrouped case
                if ($nextRow.length) {
                    nextRowIndex = $nextRow.prop('rowIndex') - 1;
                } else if (!this.editable) {
                    nextRowIndex = borderRowIndex;
                } else if (!options.forceCreate && !record.isDirty()) {
                    this.trigger_up('discard_changes', {
                        recordID: recordID,
                        onSuccess: this.trigger_up.bind(this, 'activate_next_widget', { side: side }),
                    });
                    return;
                }
            } else {
                // grouped case
                var $directNextRow = $currentRow.next();
                if (next && this.editable === "bottom" && $directNextRow.hasClass('o_add_record_row')) {
                    // the next row is the 'Add a line' row (i.e. the current one is the last record
                    // row of the group)
                    if (options.forceCreate || record.isDirty()) {
                        // if we modified the current record, add a row to create a new record
                        groupId = $directNextRow.data('group-id');
                    } else {
                        // if we didn't change anything to the current line (e.g. we pressed TAB on
                        // each cell without modifying/entering any data), we discard that line (if
                        // it was a new one) and move to the first record of the next group
                        nextRowIndex = ($nextRow.prop('rowIndex') - 1) || null;
                        this.trigger_up('discard_changes', {
                            recordID: recordID,
                            onSuccess: () => {
                                if (nextRowIndex !== null) {
                                    if (!record.res_id) {
                                        // the current record was a new one, so we decrement
                                        // nextRowIndex as that row has been removed meanwhile
                                        nextRowIndex--;
                                    }
                                    this._selectCell(nextRowIndex, cellIndex, cellOptions);
                                } else {
                                    // we were in the last group, so go back to the top
                                    this._selectCell(borderRowIndex, cellIndex, cellOptions);
                                }
                            },
                        });
                        return;
                    }
                } else {
                    // there is no 'Add a line' row (i.e. the create feature is disabled), or the
                    // list is editable="top", we focus the first record of the next group if any,
                    // or we go back to the top of the list
                    nextRowIndex = $nextRow.length ?
                        ($nextRow.prop('rowIndex') - 1) :
                        borderRowIndex;
                }
            }

            // if there is a (record) row to select, select it, otherwise, add a new record (in the
            // correct group, if the view is grouped)
            if (nextRowIndex !== null) {
                // cellOptions.force = true;
                this._selectCell(nextRowIndex, cellIndex, cellOptions);
            } else if (this.editable) {
                // if for some reason (e.g. create feature is disabled) we can't add a new
                // record, select the first record row
                this.unselectRow().then(this.trigger_up.bind(this, 'add_record', {
                    groupId: groupId,
                    onFail: this._selectCell.bind(this, borderRowIndex, cellIndex, cellOptions),
                }));
            }
        });
    },
    /**
     * Override to compute the (relative or absolute) width of each column.
     *
     * @override
     * @private
     */
    _processColumns: function () {
        const oldColumns = this.columns;
        this._super.apply(this, arguments);
        // check if stored widths still apply
        if (this.columnWidths && oldColumns && oldColumns.length === this.columns.length) {
            for (let i = 0; i < oldColumns.length; i++) {
                if (oldColumns[i] !== this.columns[i]) {
                    this.columnWidths = false; // columns changed, so forget stored widths
                    break;
                }
            }
        } else {
            this.columnWidths = false; // columns changed, so forget stored widths
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
                    // update currentID taking moved line into account
                    if (self.currentRow !== null) {
                        var currentID = self.state.data[self.currentRow].id;
                        self.currentRow = self._getRow(currentID).index();
                    }
                    self.unselectRow().then(function () {
                        self._moveRecord(ui.item.data('id'), ui.item.index());
                    });
                },
            });
        }
        return $body;
    },
    /**
     * @override
     * @private
     */
    _renderFooter: function () {
        const $footer = this._super.apply(this, arguments);
        if (this.addTrashIcon) {
            $footer.find('tr').append($('<td>'));
        }
        return $footer;
    },
    /**
     * Override to optionally add a th in the header for the remove icon column.
     *
     * @override
     * @private
     */
    _renderHeader: function () {
        var $thead = this._super.apply(this, arguments);
        if (this.addTrashIcon) {
            $thead.find('tr').append($('<th>', {class: 'o_list_record_remove_header'}));
        }
        return $thead;
    },
    /**
     * Overriden to add a resize handle in editable list column headers.
     * Only applies to headers containing text.
     *
     * @override
     * @private
     */
    _renderHeaderCell: function () {
        const $th = this._super.apply(this, arguments);
        if ($th[0].innerHTML.length && this._hasVisibleRecords(this.state)) {
            const resizeHandle = document.createElement('span');
            resizeHandle.classList = 'o_resize';
            resizeHandle.onclick = this._onClickResize.bind(this);
            resizeHandle.onmousedown = this._onStartResize.bind(this);
            $th.append(resizeHandle);
        }
        return $th;
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
                $('<button>', {'class': 'fa fa-times', 'name': 'unlink', 'aria-label': _t('Unlink row ') + (index + 1)}) :
                $('<button>', {'class': 'fa fa-trash-o', 'name': 'delete', 'aria-label': _t('Delete row ') + (index + 1)});
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
        this.currentRow = null;
        return this._super.apply(this, arguments).then(() => {
            const table = this.el.getElementsByTagName('table')[0];
            if (table) {
                table.classList.toggle('o_empty_list', !this._hasVisibleRecords(this.state));
                this._freezeColumnWidths();
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
        var recordID = this._getRecordID(rowIndex);

        // Select the row then activate the widget in the correct cell
        var self = this;
        return this._selectRow(rowIndex).then(function () {
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
        if (!this.columnWidths) {
            // we don't want the column widths to change when selecting rows
            this._storeColumnWidths();
        }
        var recordId = this._getRecordID(rowIndex);
        // To select a row, the currently selected one must be unselected first
        var self = this;
        return this.unselectRow().then(noSelectNext => {
            if (noSelectNext) {
                return Promise.resolve();
            }
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
                    onSuccess: function () {
                        self._disableRecordSelectors();
                        resolve();
                    },
                });
            });
        });
    },
    /**
     * Set a maximum width on the largest columns in the list in case the table
     * is overflowing. The idea is to shrink largest columns first, but to
     * ensure that they are still the largest at the end (maybe in equal measure
     * with other columns).
     *
     * @private
     * @returns {integer[]} width (in px) of each column s.t. the table doesn't
     *   overflow
     */
    _squeezeTable: function () {
        const table = this.el.getElementsByTagName('table')[0];

        // Toggle a className used to remove style that could interfer with the ideal width
        // computation algorithm (e.g. prevent text fields from being wrapped during the
        // computation, to prevent them from being completely crushed)
        table.classList.add('o_list_computing_widths');

        const thead = table.getElementsByTagName('thead')[0];
        const thElements = [...thead.getElementsByTagName('th')];
        const columnWidths = thElements.map(th => th.offsetWidth);
        const getWidth = th => columnWidths[thElements.indexOf(th)] || 0;
        const getTotalWidth = () => thElements.reduce((tot, th, i) => tot + columnWidths[i], 0);
        const shrinkColumns = (columns, width) => {
            let thresholdReached = false;
            columns.forEach(th => {
                const index = thElements.indexOf(th);
                let maxWidth = columnWidths[index] - Math.ceil(width / columns.length);
                if (maxWidth < 92) { // prevent the columns from shrinking under 92px (~ date field)
                    maxWidth = 92;
                    thresholdReached = true;
                }
                th.style.maxWidth = `${maxWidth}px`;
                columnWidths[index] = maxWidth;
            });
            return thresholdReached;
        };
        // Sort columns, largest first
        const sortedThs = [...thead.getElementsByTagName('th')]
            .sort((a, b) => getWidth(b) - getWidth(a));
        const allowedWidth = table.parentNode.offsetWidth;

        let totalWidth = getTotalWidth();
        let stop = false;
        let index = 0;
        while (totalWidth > allowedWidth && !stop) {
            // Find the largest columns
            index++;
            const largests = sortedThs.slice(0, index);
            while (getWidth(largests[0]) === getWidth(sortedThs[index])) {
                largests.push(sortedThs[index]);
                index++;
            }

            // Compute the number of px to remove from the largest columns
            const nextLargest = sortedThs[index]; // largest column when omitting those in largests
            const totalToRemove = totalWidth - allowedWidth;
            const canRemove = (getWidth(largests[0]) - getWidth(nextLargest)) * largests.length;

            // Shrink the largests columns
            stop = shrinkColumns(largests, Math.min(totalToRemove, canRemove));

            totalWidth = getTotalWidth();
        }

        // We are no longer computing widths, so restore the normal style
        table.classList.remove('o_list_computing_widths');

        return columnWidths;
    },
    /**
     * @private
     */
    _storeColumnWidths: function () {
        this.columnWidths = this.$('thead th').toArray().map(function (th) {
            return $(th).outerWidth();
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
        // This method can be called when selecting the parent of the link.
        // We need to ensure that the link is the actual target
        const target = ev.target.tagName !== 'A' ? ev.target.getElementsByTagName('A')[0] : ev.target;
        const groupId = target.dataset.groupId;
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
        var $td = $(event.currentTarget);
        var $tr = $td.parent();
        var rowIndex = $tr.prop('rowIndex') - 1;
        if (!this._isRecordEditable($tr.data('id')) || $(event.target).prop('special_click')) {
            return;
        }
        var fieldIndex = Math.max($tr.find('.o_field_cell').index($td), 0);
        this._selectCell(rowIndex, fieldIndex, {event: event});
    },
    /**
     * We want to override any default mouse behaviour when clicking on the resize handles
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickResize: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
    },
    /**
     * We need to manually unselect row, because no one else would do it
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
        const $target = $(ev.currentTarget);
        const $tr = $target.closest('tr');
        const recordEditable = this._isRecordEditable($tr.data('id'));

        if (recordEditable && ev.keyCode === $.ui.keyCode.ENTER && $tr.hasClass('o_selected_row')) {
            // enter on a textarea for example, let it bubble
            return;
        }

        if (recordEditable && ev.keyCode === $.ui.keyCode.ENTER &&
            !$tr.hasClass('o_selected_row') && !$tr.hasClass('o_group_header')) {
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
        switch (e.keyCode) {
            case $.ui.keyCode.ENTER:
                e.stopPropagation();
                e.preventDefault();
                this._onAddRecord(e);
                break;
        }
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
        // Don't stop the propagation when navigating up while not editing any row
        if (this.currentRow === null && ev.data.direction === 'up') {
            return;
        }
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
                if (this.currentFieldIndex + 1 < this.columns.length) {
                    this._selectCell(this.currentRow, this.currentFieldIndex + 1, {wrap: false})
                        .guardedCatch(this._moveToNextLine.bind(this));
                } else {
                    this._moveToNextLine();
                }
                break;
            case 'next_line':
                // If the list is readonly and the current is the only record editable, we unselect the line
                if (!this.editable && this.selection.length === 1 &&
                    this._getRecordID(this.currentRow) === ev.target.dataPointID) {
                    this.unselectRow();
                } else {
                    this._moveToNextLine({ forceCreate: true });
                }
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
                        self._enableRecordSelectors();
                        var recordId = self._getRecordID(rowIndex);
                        if (recordId) {
                            var correspondingRow = self._getRow(recordId);
                            correspondingRow.children().eq(cellIndex).focus();
                        } else if (self.currentGroupId) {
                            self.$('a[data-group-id="' + self.currentGroupId + '"]').focus();
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
     * React to window resize events by recomputing the width of each column.
     *
     * @private
     */
    _onResize: function () {
        this.columnWidths = false;
        this._freezeColumnWidths();
    },
    /**
     * If the list view editable, just let the event bubble. We don't want to
     * open the record in this case anyway.
     *
     * @override
     * @private
     */
    _onRowClicked: function (ev) {
        if (!this._isRecordEditable(ev.currentTarget.dataset.id)) {
            // If there is an edited record, tries to save it and do not open the clicked record
            if (this.getEditableRecordID()) {
                this.unselectRow();
            } else {
                this._super.apply(this, arguments);
            }
        }
    },
    /**
     * Overrides to prevent from sorting if we are currently editing a record.
     *
     * @override
     * @private
     */
    _onSortColumn: function () {
        if (this.currentRow === null && !this.isResizing) {
            this._super.apply(this, arguments);
        }
    },
    /**
     * Handles the resize feature on the column headers
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onStartResize: function (ev) {
        // Only triggered by left mouse button
        if (ev.which !== 1) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();

        this.isResizing = true;

        const table = this.el.getElementsByTagName('table')[0];
        const th = ev.target.closest('th');
        table.style.width = `${table.offsetWidth}px`;
        const thPosition = [...th.parentNode.children].indexOf(th);
        const resizingColumnElements = [...table.getElementsByTagName('tr')]
            .filter(tr => tr.children.length === th.parentNode.children.length)
            .map(tr => tr.children[thPosition]);
        const optionalDropdown = this.el.getElementsByClassName('o_optional_columns')[0];
        const initialX = ev.pageX;
        const initialWidth = th.offsetWidth;
        const initialTableWidth = table.offsetWidth;
        const initialDropdownX = optionalDropdown ? optionalDropdown.offsetLeft : null;
        const resizeStoppingEvents = [
            'keydown',
            'mousedown',
            'mouseup',
        ];

        // Apply classes to table and selected column
        table.classList.add('o_resizing');
        resizingColumnElements.forEach(el => el.classList.add('o_column_resizing'));

        // Mousemove event : resize header
        const resizeHeader = ev => {
            ev.preventDefault();
            ev.stopPropagation();
            const delta = ev.pageX - initialX;
            const newWidth = Math.max(10, initialWidth + delta);
            const tableDelta = newWidth - initialWidth;
            th.style.width = `${newWidth}px`;
            table.style.width = `${initialTableWidth + tableDelta}px`;
            if (optionalDropdown) {
                optionalDropdown.style.left = `${initialDropdownX + tableDelta}px`;
            }
        };
        this._addEventListener('mousemove', window, resizeHeader);

        // Mouse or keyboard events : stop resize
        const stopResize = ev => {
            // Ignores the initial 'left mouse button down' event in order
            // to not instantly remove the listener
            if (ev.type === 'mousedown' && ev.which === 1) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            // We need a small timeout to not trigger a click on column header
            clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(() => {
                this.isResizing = false;
            }, 100);
            window.removeEventListener('mousemove', resizeHeader);
            table.classList.remove('o_resizing');
            resizingColumnElements.forEach(el => el.classList.remove('o_column_resizing'));
            resizeStoppingEvents.forEach(stoppingEvent => {
                window.removeEventListener(stoppingEvent, stopResize);
            });

            // we remove the focus to make sure that the there is no focus inside
            // the tr.  If that is the case, there is some css to darken the whole
            // thead, and it looks quite weird with the small css hover effect.
            document.activeElement.blur();
        };
        // We have to listen to several events to properly stop the resizing function. Those are:
        // - mousedown (e.g. pressing right click)
        // - mouseup : logical flow of the resizing feature (drag & drop)
        // - keydown : (e.g. pressing 'Alt' + 'Tab' or 'Windows' key)
        resizeStoppingEvents.forEach(stoppingEvent => {
            this._addEventListener(stoppingEvent, window, stopResize);
        });
    },
    /**
     * Unselect the row before adding the optional column to the listview
     *
     * @override
     * @private
     */
    _onToggleOptionalColumnDropdown: function (ev) {
        this.unselectRow().then(this._super.bind(this, ev));
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
        // ignore clicks on readonly lists with no selected rows
        if (!this.isEditable()) {
            return;
        }

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
