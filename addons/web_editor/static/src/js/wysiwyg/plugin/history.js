odoo.define('web_editor.wysiwyg.plugin.history', function (require) {
'use strict';

var Plugins = require('web_editor.wysiwyg.plugins');
var registry = require('web_editor.wysiwyg.plugin.registry');


var HistoryPlugin = Plugins.history.extend({
    /**
     * Apply a snapshot.
     *
     * @override
     */
    applySnapshot: function () {
        this.context.invoke('MediaPlugin.hidePopovers');
        try {
            this._super.apply(this, arguments);
        } catch (e) {
            console.error(e);
        }
        this.context.invoke('editor.focus');
    },
    /**
     * Clear the history.
     *
     * @override
     */
    clear: function () {
        this.stack = [];
        this.stackOffset = -1;
        this.recordUndo();
    },
    /**
     * Get the current history stack and the current offset.
     *
     * @returns {Object} {stack: Object, stackOffset: Integer}
     */
    getHistoryStep: function () {
        return {
            stack: this.stack,
            stackOffset: this.stackOffset,
        };
    },
    /**
     * Prevent errors with first snapshot.
     *
     * @override
     */
    makeSnapshot: function () {
        var rng = $.summernote.range.create(this.editable);
        var snapshot = this._super();
        if (rng.sc === this.editable || $(rng.sc).has(this.editable).length) {
            snapshot.bookmark.s.path = snapshot.bookmark.e.path = [0];
            snapshot.bookmark.s.offset = snapshot.bookmark.e.offset = 0;
        }
        return snapshot;
    },
    /**
     * @override
     */
    recordUndo: function () {
        if (!this.stack[this.stackOffset] || this.$editable.html() !== this.stack[this.stackOffset].contents) {
            this._super();
        }
    },
    /**
     * @override
     */
    undo: function () {
        if (this.stackOffset > 0) {
            this.stackOffset--;
        }
        this.applySnapshot(this.stack[this.stackOffset]);
    },
});

registry.add('HistoryPlugin', HistoryPlugin);

return HistoryPlugin;

});
