odoo.define('web_editor.wysiwyg.plugin.table', function (require) {
'use strict';

var Plugins = require('web_editor.wysiwyg.plugins');
var registry = require('web_editor.wysiwyg.plugin.registry');

var dom = $.summernote.dom;


var TablePlugin = Plugins.table.extend({

    initialize: function () {
        this._super.apply(this, arguments);
        var self = this;
        // We need setTimeout to make sure to initialize after HelperPlugin and HistoryPlugin
        setTimeout(function () {
            // contentEditable fail for image and font in table
            // user must use right arrow the number of space but without feedback
            self.$editable.find('td:has(img, span.fa)').each(function () {
                if (this.firstChild && !this.firstChild.tagName) {
                    var startSpace = self.context.invoke('HelperPlugin.getRegex', 'startSpace');
                    this.firstChild.textContent = this.firstChild.textContent.replace(startSpace, ' ');
                }
                if (this.lastChild && !this.lastChild.tagName) {
                    var endSpace = self.context.invoke('HelperPlugin.getRegex', 'endSpace');
                    this.lastChild.textContent = this.lastChild.textContent.replace(endSpace, ' ');
                }
            });
            self.context.invoke('HistoryPlugin.clear');
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a new col and
     * wrap contents of the new cells in p elements.
     *
     * @see summernote library
     *
     * @override
     * @param {WrappedRange} rng
     * @param {String('left'|'right')} position
     */
    addCol: function (rng, position) {
        this._super.apply(this, arguments);
        var cell = dom.ancestor(rng.commonAncestor(), dom.isCell);
        var table = dom.ancestor(cell, function (n) {
            return n.tagName === 'TABLE';
        });
        var newColIndex = $(cell)[position === 'right' ? 'next' : 'prev']('td').index() + 1;
        $(table).find('td:nth-child(' + newColIndex + ')').contents().wrap('<p></p>');
    },
    /**
     * Add a new row and
     * wrap contents of the new cells in p elements.
     *
     * @see summernote library
     *
     * @override
     * @param {WrappedRange} rng
     * @param {String('top'|'bottom')} position
     */
    addRow: function (rng, position) {
        this._super.apply(this, arguments);
        var row = dom.ancestor(rng.commonAncestor(), dom.isCell).parentElement;
        $(row)[position === 'bottom' ? 'next' : 'prev']('tr').find('td').contents().wrap('<p></p>');
    },
    /**
     * Create empty table element and
     * wrap the contents of all cells in p elements.
     *
     * @see summernote library
     *
     * @override
     * @param {Number} rowCount
     * @param {Number} colCount
     * @returns {Node} table
     */
    createTable: function () {
        var table = this._super.apply(this, arguments);
        $(table).find('td').contents().wrap('<p></p>');
        return table;
    },
    /**
     * @see summernote library
     *
     * @override
     */
    deleteCol: function () {
        var range = this.context.invoke('editor.createRange');

        // Delete the last remaining column === delete the table
        var cell = dom.ancestor(range.commonAncestor(), dom.isCell);
        if (cell && !cell.previousElementSibling && !cell.nextElementSibling) {
            return this.deleteTable();
        }
        var neighbor = cell.previousElementSibling || cell.nextElementSibling;

        this._super.apply(this, arguments);

        // Put the range back on the previous or next cell after deleting
        // to allow chain-removing
        range = this.context.invoke('editor.createRange');
        if (range.sc.tagName !== 'TD' && neighbor) {
            range = this.context.invoke('editor.setRange', neighbor, 0);
            range.normalize().select();
        }
    },
    /**
     * @see summernote library
     *
     * @override
     */
    deleteRow: function () {
        var range = this.context.invoke('editor.createRange');

        // Delete the last remaining row === delete the table
        var row = dom.ancestor(range.commonAncestor(), function (n) {
            return n.tagName === 'TR';
        });
        if (row && !row.previousElementSibling && !row.nextElementSibling) {
            return this.deleteTable();
        }
        var neighbor = row.previousElementSibling || row.nextElementSibling;

        this._super.apply(this, arguments);

        // Put the range back on the previous or next row after deleting
        // to allow chain-removing
        range = this.context.invoke('editor.createRange');
        if (range.sc.tagName !== 'TR' && neighbor) {
            range = this.context.invoke('editor.setRange', neighbor, 0);
            range.normalize().select();
        }
    },
    /**
     * Delete the table in range.
     */
    deleteTable: function () {
        var range = this.context.invoke('editor.createRange');
        var cell = dom.ancestor(range.commonAncestor(), dom.isCell);
        var table = $(cell).closest('table')[0];

        var point = this.context.invoke('HelperPlugin.removeBlockNode', table);
        range = this.context.invoke('editor.setRange', point.node, point.offset);
        range.normalize().select();
    },
    /**
     * Insert a table.
     * Note: adds <p><br></p> before/after the table if the table
     * has nothing brefore/after it, so as to allow the carret to move there.
     *
     * @param {String} dim dimension of table (ex : "5x5")
     */
    insertTable: function (dim) {
        var dimension = dim.split('x');
        var table = this.createTable(dimension[0], dimension[1], this.options);
        this.context.invoke('HelperPlugin.insertBlockNode', table);
        var p;
        if (!table.previousElementSibling) {
            p = this.document.createElement('p');
            $(p).append(this.document.createElement('br'));
            $(table).before(p);
        }
        if (!table.nextElementSibling) {
            p = this.document.createElement('p');
            $(p).append(this.document.createElement('br'));
            $(table).after(p);
        }
        var range = this.context.invoke('editor.setRange', $(table).find('td')[0], 0);
        range.normalize().select();
        this.context.invoke('editor.saveRange');
    },
});


var TablePopover = Plugins.tablePopover.extend({
    events: _.defaults({
        'summernote.scroll': '_onScroll',
    }, Plugins.tablePopover.prototype.events),

    /**
     * Update the table's popover and its position.
     *
     * @override
     * @param {Node} target
     * @returns {false|Node} the selected cell (on which to display the popover)
     */
    update: function (target) {
        if (!target || this.context.isDisabled()) {
            return false;
        }
        var cell = dom.ancestor(target, dom.isCell);
        if (!!cell && this.options.isEditableNode(cell)) {
            var pos = $(cell).offset();
            var posContainer = $(this.options.container).offset();
            pos.left = pos.left - posContainer.left + 10;
            pos.top = pos.top - posContainer.top + $(cell).outerHeight() - 4;

            this.lastPos = this.context.invoke('HelperPlugin.makePoint', target, $(target).offset());

            this.$popover.css({
                display: 'block',
                left: pos.left,
                top: pos.top,
            });
        } else {
            this.hide();
        }
        return cell;
    },
    /**
     * Update the target table and its popover.
     *
     * @private
     */
    _onScroll: function () {
        var range = this.context.invoke('editor.createRange');
        var target = dom.ancestor(range.sc, dom.isCell);
        if (!target || target === this.editable) {
            return;
        }
        if (this.lastPos && this.lastPos.target === target && $(target).offset()) {
            var newTop = $(target).offset().top;
            var movement = this.lastPos.offset.top - newTop;
            if (movement && this.mousePosition) {
                this.mousePosition.pageY -= movement;
            }
        }
        return this.update(target);
    },
});


registry.add('TablePlugin', TablePlugin);
registry.add('TablePopover', TablePopover);
registry.add('tablePopover', null);

return TablePlugin;

});
