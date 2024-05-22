odoo.define('web_editor.wysiwyg.snippets', function (require) {
'use strict';
var editor = require('web_editor.editor');
var Wysiwyg = require('web_editor.wysiwyg');


Wysiwyg.include({
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.Editor = editor.Class;
        if (!this.options.toolbarHandler) {
            this.options.toolbarHandler = $('#web_editor-top-edit');
        }
    },
    start: async function () {
        if (this.options.snippets) {
            var self = this;
            this.editor = new (this.Editor)(this, this.options);
            this.$editor = this.editor.rte.editable();
            const $body = this.$editor[0] ? this.$editor[0].ownerDocument.body : document.body;
            await this.editor.prependTo($body);
            this._relocateEditorBar();
            this.$el.on('content_changed', function (e) {
                self.trigger_up('wysiwyg_change');
            });
        } else {
            return this._super();
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _relocateEditorBar: function () {
        if (!this.options.toolbarHandler.length) {
            this.options.toolbarHandler = $('.o_we_snippet_text_tools');
        }
        this.options.toolbarHandler.append(this.editor.$el);

        // TODO the next four lines are a huge hack: since the editor.$el
        // is repositioned, the snippetsMenu elements are not at the
        // correct position anymore if it was repositioned outside of it...
        // the whole logic has to be refactored... hopefully not needed anymore
        // with editor team changes
        if (this.editor.snippetsMenu && !this.editor.snippetsMenu.$el.has(this.options.toolbarHandler).length) {
            this.editor.snippetsMenu.$el.insertAfter(this.options.toolbarHandler);
            this.editor.snippetsMenu.$snippetEditorArea.insertAfter(this.editor.snippetsMenu.$el);
        }
    },
});

});
