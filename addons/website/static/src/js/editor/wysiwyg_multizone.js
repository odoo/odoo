odoo.define('web_editor.wysiwyg.multizone', function (require) {
'use strict';
var concurrency = require('web.concurrency');
var core = require('web.core');
var editor = require('web_editor.editor');
var Wysiwyg = require('web_editor.wysiwyg');


/**
 * HtmlEditor
 * Intended to edit HTML content. This widget uses the Wysiwyg editor
 * improved by odoo.
 *
 * class editable: o_editable
 * class non editable: o_not_editable
 *
 */
var WysiwygMultizone = Wysiwyg.extend({
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.params = params;
    },
    willStart: async function () {
        await this._super.apply(this, arguments);
        this.editor = new (editor.Class)(this);
        return this.editor.prependTo(document.body);
    },
    start: function () {
        $('#web_editor-toolbars').prependTo('#web_editor-top-edit');
    }
});

return WysiwygMultizone;
});
