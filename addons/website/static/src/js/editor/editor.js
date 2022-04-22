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
    start: async function () {
        const options = {
            body: this.linkWidget.$link && this.linkWidget.$link[0].ownerDocument.body,
        };
        const result = await this._super.apply(this, arguments);
        wUtils.autocompleteWithPages(this, this.$('input[name="url"]'), options);
        return result;
    },
});
});
