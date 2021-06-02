odoo.define('mail.FilterMenu', function (require) {
"use strict";

var FilterMenu = require('web.FilterMenu');

FilterMenu.include({
    init: function () {
        this._super.apply(this, arguments);
        //remove messages from custom filters
        this.fields = _.pick(this.fields, function (field, name) {
            return field.relation !== 'mail.message' && name !== 'message_ids';
        });
    },
});

});
