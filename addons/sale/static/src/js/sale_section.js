odoo.define('sale.sale_section', function (require) {
"use strict";
var core = require('web.core');
var ListRenderer = require('web.ListRenderer');

ListRenderer.include({
    // We don't want to select the cell for note and section, we only
    // want to edit them with the dialog because they have additional fields.
    _onCellClick: function (ev) {
        var currentLine = $(ev.currentTarget.parentNode);

        var isNoteOrSection = currentLine && (
            currentLine.hasClass('is-note')
            || currentLine.hasClass('is-section')
        );

        if (isNoteOrSection) {
            return;
        }

        this._super.apply(this, arguments);
    },
    // We only want dialog edit for note and section.
    _onRowClicked: function (ev) {
        var currentLine = $(ev.currentTarget);

        var isNoteOrSection = currentLine && (
            currentLine.hasClass('is-note')
            || currentLine.hasClass('is-section')
        );

        var args = Array.prototype.slice.call(arguments);
        args.push(isNoteOrSection);
        this._super.apply(this, args);
    },
    // Disable column sorting for handle
    _onSortColumn: function (ev) {
        if (!this.handleField) {
            this._super.apply(this, arguments);
            // TODO SHT: either don't disable it, or show a warning on click, or remove the sort arrow from the columns
            // QUESTION: Should we disable sorting when there is a handle, or should we disable handle when there is a different sorting?
        }
    },
    // If not a product line (= for section or note)
    // the "name" column is the only one that should be displayed
    // between the handle and the delete button.
    _renderBodyCell: function (record, node, index, options) {
        var $cell = this._super.apply(this, arguments);

        if (record.model === "sale.order.line" && record.data['line_type'] !== 'product') {
            if ($cell.hasClass('o_handle_cell')) {
                return $cell;
            } else if ($cell.hasClass('product_name')) {
                var nbrColumns = this.addTrashIcon ? this._getNumberOfCols() - 2: this._getNumberOfCols();
                $cell.attr('colspan', nbrColumns);
            } else {
                return $cell.addClass('o_hidden');
            }
        }
        return $cell;
    },
});

});