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
     * @returns {Deferred}
     */
    setRowMode: function (recordID, mode) {
        var self = this;
        var rowIndex = _.findIndex(this.state.data, {id: recordID});
        if (rowIndex < 0) {
            return;
        }
        var editMode = (mode === 'edit');
        var record = this.state.data[rowIndex];

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
        if (!editMode) {
            // Force 'readonly' mode for widgets in readonly rows as
            // otherwise they default to the view mode which is 'edit' for
            // an editable list view
            options.mode = 'readonly';
        }

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
                self._unregisterModifiersElement(node, record, $td.children());
            }

            // For edit mode we only replace the content of the cell with its
            // new content (invisible fields, editable fields, ...).
            // For readonly mode, we replace the whole cell so that the
            // dimensions of the cell are not forced anymore.
            if (editMode) {
                $td.empty().append($newTd.contents());
            } else {
                self._unregisterModifiersElement(node, record, $td);
                $td.replaceWith($newTd);
            }
        });
        delete this.defs;

        // Destroy old field widgets
        _.each(oldWidgets, this._destroyFieldWidget.bind(this, record));

        // Toggle selected class here so that style is applied at the end
        $row.toggleClass('o_selected_row', editMode);

        return $.when.apply($, defs);
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
     * Move the cursor on the end of the previous line, if possible.
     * If there is no previous line, then we create a new record.
     *
     * @private
     */
    _moveToPreviousLine: function () {
        if (this.currentRow > 0) {
            this._selectCell(this.currentRow - 1, this.columns.length - 1);
        } else {
            this._unselectRow().then(this.trigger_up.bind(this, 'add_record'));
        }
    },
    /**
     * Move the cursor on the beginning of the next line, if possible.
     * If there is no next line, then we create a new record.
     *
     * @private
     */
    _moveToNextLine: function () {
        if (this.currentRow < this.state.data.length - 1) {
            this._selectCell(this.currentRow + 1, 0);
        } else {
            this._unselectRow().then(this.trigger_up.bind(this, 'add_record'));
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
     * @param {boolean} [wrap=true] if true and no widget could be selected from
     *   the colIndex to the last column, then we wrap around and try to select
     *   a widget starting from the beginning
     * @return {Deferred} fails if no cell could be selected
     */
    _selectCell: function (rowIndex, colIndex, wrap) {
        // Do nothing if the user tries to select current cell
        if (rowIndex === this.currentRow && colIndex === this.currentCol) {
            return $.when();
        }
        wrap = wrap === undefined ? true : wrap;

        // Select the row then activate the widget in the correct cell
        var self = this;
        return this._selectRow(rowIndex).then(function () {
            var record = self.state.data[rowIndex];
            var correctedIndex = colIndex - getNbButtonBefore(colIndex);
            var fieldIndex = self._activateFieldWidget(record, correctedIndex, {inc: 1, wrap: wrap});

            if (fieldIndex < 0) {
                return $.Deferred().reject();
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
     * @returns {Deferred}
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
            var def = $.Deferred();
            self.trigger_up('edit_line', {
                recordID: record.id,
                onSuccess: def.resolve.bind(def),
            });
            return def;
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
                    this._selectCell(this.currentRow - 1, this.currentCol);
                }
                break;
            case 'right':
                if (this.currentCol + 1 < this.columns.length) {
                    this._selectCell(this.currentRow, this.currentCol + 1);
                }
                break;
            case 'down':
                if (this.currentRow < this.state.data.length - 1) {
                    this._selectCell(this.currentRow + 1, this.currentCol);
                }
                break;
            case 'left':
                if (this.currentCol > 0) {
                    this._selectCell(this.currentRow, this.currentCol - 1);
                }
                break;
            case 'previous':
                if (this.currentCol > 0) {
                    this._selectCell(this.currentRow, this.currentCol - 1, false)
                        .fail(this._moveToPreviousLine.bind(this));
                } else {
                    this._moveToPreviousLine();
                }
                break;
            case 'next':
                if (this.currentCol + 1 < this.columns.length) {
                    this._selectCell(this.currentRow, this.currentCol + 1, false)
                        .fail(this._moveToNextLine.bind(this));
                } else {
                    this._moveToNextLine();
                }
                break;
            case 'next_line':
                this._moveToNextLine();
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
