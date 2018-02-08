odoo.define('website.editor', function (require) {
'use strict';

var weWidgets = require('web_editor.widget');
var wUtils = require('website.utils');

weWidgets.LinkDialog.include({
    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    start: function () {
        wUtils.autocompleteWithPages(this, this.$('input[name="url"]'));
        return this._super.apply(this, arguments);
    },
});
});
