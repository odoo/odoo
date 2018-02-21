odoo.define('website.editor', function (require) {
'use strict';

var widget = require('web_editor.widget');
var wUtils = require('website.utils');

widget.LinkDialog.include({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Allows the URL input to propose existing website pages.
     *
     * @override
     */
    bind_data: function () {
        wUtils.autocompleteWithPages(this, this.$('#o_link_dialog_url_input'));
        return this._super.apply(this, arguments);
    },
});
});
