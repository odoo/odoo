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
            await this.editor.prependTo(this.$editor[0].ownerDocument.body);
            this.options.toolbarHandler.append(this.editor.$el);
            this.$el.on('content_changed', function (e) {
                var $editable = $(e.target).closest('[data-oe-model], .o_editable');
                $editable.addClass('o_dirty');
                self.trigger_up('wysiwyg_change');
            });
        } else {
            return this._super();
        }
    },
});

});
