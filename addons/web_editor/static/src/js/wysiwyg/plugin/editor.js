odoo.define('web_editor.wysiwyg.plugin.editor', function (require) {
'use strict';

var Plugins = require('web_editor.wysiwyg.plugins');
var registry = require('web_editor.wysiwyg.plugin.registry');
var TablePlugin = require('web_editor.wysiwyg.plugin.table');


var NewSummernoteEditor = Plugins.editor.extend({
    //--------------------------------------------------------------------------
    // Public summernote module API
    //--------------------------------------------------------------------------

    initialize: function () {
        var self = this;
        this.history = this.context.modules.HistoryPlugin;
        this.dropzone = this.context.modules.DropzonePlugin;

        this.insertTable = this.wrapCommand(this._insertTable.bind(this));
        this.insertOrderedList = this.wrapCommand(this._insertOrderedList.bind(this));
        this.insertUnorderedList = this.wrapCommand(this._insertUnorderedList.bind(this));
        this.insertCheckList = this.wrapCommand(this._insertCheckList.bind(this));
        this.indent = this.wrapCommand(this._indent.bind(this));
        this.outdent = this.wrapCommand(this._outdent.bind(this));
        this.table = new TablePlugin(this.context);
        this.hasFocus = this._hasFocus.bind(this);

        this._makeTextCommand('formatBlock');
        this._makeTextCommand('removeFormat');
        _.each('bold,italic,underline,strikethrough,superscript,subscript'.split(','), function (sCmd) {
            self._makeTextCommand('formatText', sCmd);
        });
        _.each('justifyLeft,justifyCenter,justifyRight,justifyFull'.split(','), function (sCmd) {
            self._makeTextCommand('formatBlockStyle', sCmd);
        });

        this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Hide all popovers.
     */
    hidePopover: function () {
        this.context.invoke('MediaPlugin.hidePopovers');
        this.context.invoke('LinkPopover.hide');
    },
    /*
     * Focus the editor.
     */
    focus: function () {
        // [workaround] Screen will move when page is scolled in IE.
        //  - do focus when not focused
        if (!this.hasFocus()) {
            var range = $.summernote.range.create();
            if (range) {
                $(range.sc).closest('[contenteditable]').focus();
                range.select();
            } else {
                this.$editable.focus();
            }
        }
    },
    /**
     * Fix double-undo (CTRL-Z) issue with Odoo integration.
     *
     * @override
     */
    undo: function () {
        this.createRange();
        this._super();
    },
    /**
     * Set the range at the given nodes and offsets.
     * If no `ec` is specified, the range is collapsed on start.
     * Note: Does NOT select the range.
     *
     * @param {Node} sc
     * @param {Number} so
     * @param {Node} [ec]
     * @param {Number} [eo]
     * @returns {Object} range
     */
    setRange: function (sc, so, ec, eo) {
        var range = this.createRange();
        range.sc = sc;
        range.so = so;
        range.ec = ec || sc;
        range.eo = eo || so;
        return range;
    },
    /**
     * Remove a link and preserve its text contents.
     */
    unlink: function () {
        this.beforeCommand();
        this.context.invoke('LinkPlugin.unlink');
        this.afterCommand();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns true if editable area has focus.
     *
     * @private
     * @returns {Boolean}
     */
    _hasFocus: function () {
        return this.$editable.is(':focus') || !!this.$editable.find('[contenteditable]:focus').length;
    },
    /**
     * Indent a list or a format node.
     *
     * @private
     * @returns {false|Node[]} contents of list/indented item
     */
    _indent: function () {
        return this.context.invoke('BulletPlugin.indent');
    },
    /**
     * Insert a checklist.
     *
     * @private
     */
    _insertCheckList: function () {
        this.context.invoke('BulletPlugin.insertList', 'checklist');
    },
    /**
     * Insert an ordered list.
     *
     * @private
     */
    _insertOrderedList: function () {
        this.context.invoke('BulletPlugin.insertList', 'ol');
    },
    /**
     * Insert table (respecting unbreakable node rules).
     *
     * @private
     * @param {string} dim (eg: 3x3)
     */
    _insertTable: function (dim) {
        this.context.invoke('TablePlugin.insertTable', dim);
    },
    /**
     * Insert an ordered list.
     *
     * @private
     */
    _insertUnorderedList: function () {
        this.context.invoke('BulletPlugin.insertList', 'ul');
    },
    /**
     * Adds a TextPlugin command to the editor object.
     * The command will exist in the editor object under the name
     * arg if specified, or commandName otherwise.
     *
     * @param {String} commandName
     * @param {String} arg
     */
    _makeTextCommand: function (commandName, arg) {
        var self = this;
        this[arg || commandName] = self.wrapCommand(function (value) {
            self.context.invoke('TextPlugin.' + commandName, arg || value, value);
        });
    },
    /**
     * Outdent a list or a format node.
     *
     * @private
     * @returns {false|Node[]} contents of list/outdented item
     */
    _outdent: function () {
        return this.context.invoke('BulletPlugin.outdent');
    },
});

// Override Summernote default editor
registry.add('editor', NewSummernoteEditor);

return NewSummernoteEditor;

});
