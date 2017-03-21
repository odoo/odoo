odoo.define('mail.BasicView', function (require) {
"use strict";

var BasicView = require('web.BasicView');

var mailWidgets = ['mail_followers', 'mail_thread', 'mail_activity', 'kanban_activity'];

BasicView.include({
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        this.mailFields = {};
        for (var fieldName in viewInfo.fieldsInfo) {
            var fieldInfo = viewInfo.fieldsInfo[fieldName];
            if (_.contains(mailWidgets, fieldInfo.widget)) {
                this.mailFields[fieldInfo.widget] = fieldName;
                fieldInfo.__no_fetch = true;
            }
        }
        this.rendererParams.activeActions = this.controllerParams.activeActions;
        this.rendererParams.mailFields = this.mailFields;
    },
});

});
