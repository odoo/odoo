odoo.define('web_editor.wysiwyg.plugin.toolbar', function (require) {
'use strict';

var Plugins = require('web_editor.wysiwyg.plugins');
var registry = require('web_editor.wysiwyg.plugin.registry');

var dom = $.summernote.dom;


var ToolbarPlugin = Plugins.toolbar.extend({
    events: {
        'summernote.mouseup': 'update',
        'summernote.keyup': 'update',
        'summernote.change': 'update',
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    initialize: function () {
        this._super();
        this.update();
    },
    /**
     * Update the toolbar (enabled/disabled).
     */
    update: function () {
        var $btn = this.$toolbar.children().not('.note-history, .note-view').find('button');
        var target = this.context.invoke('editor.restoreTarget') || this.context.invoke('editor.createRange').sc;

        if (!target || !$.contains(this.editable, target) || !this.options.isEditableNode(target)) {
            $btn.addClass('o_disabled');
            return;
        }

        $btn.removeClass('o_disabled');

        if (!target || !this.options.displayPopover(target)) {
            $btn.addClass('o_disabled');
        }

        if (dom.ancestor(target, dom.isMedia)) {
            this.$toolbar.children('.note-style, .note-font, .note-para, .note-table').addClass('o_disabled');

            $btn.find('.fa-file-image-o').parent().removeClass('o_disabled');
            if (dom.ancestor(target, dom.isFont)) {
                this.$toolbar.children('.note-color').removeClass('o_disabled');

            }
        }
    },
});

registry.add('toolbar', ToolbarPlugin);

});
