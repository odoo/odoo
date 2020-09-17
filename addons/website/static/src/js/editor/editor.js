odoo.define('website.editor', function (require) {
'use strict';

var wUtils = require('website.utils');
var LinkDialog = require('wysiwyg.widgets.LinkDialog');

LinkDialog.include({
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
