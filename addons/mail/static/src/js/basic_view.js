odoo.define('mail.BasicView', function (require) {
"use strict";

var BasicView = require('web.BasicView');

var mailWidgets = ['mail_followers', 'mail_thread', 'mail_activity', 'kanban_activity'];

BasicView.include({
    init: function() {
        this.mailFields = {};
        this._super.apply(this, arguments);
        this.rendererParams.activeActions = this.controllerParams.activeActions;
        this.rendererParams.mailFields = this.mailFields;
    },
    _processField: function(field, node) {
        if (_.contains(mailWidgets, node.attrs.widget)) {
            this.mailFields[node.attrs.widget] = node.attrs.name;
            field.__no_fetch = true;
        }
        this._super.apply(this, arguments);
    },
});

});
