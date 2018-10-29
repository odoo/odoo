odoo.define('mail.BasicView', function (require) {
"use strict";

var BasicView = require('web.BasicView');

BasicView.include({
    MAIL_WIDGETS: ['mail_followers', 'mail_thread', 'mail_activity', 'kanban_activity'],
    init: function () {
        this._super.apply(this, arguments);
        this.mailFields = {};
        var fieldsInfo = this.fieldsInfo[this.viewType];
        for (var fieldName in fieldsInfo) {
            var fieldInfo = fieldsInfo[fieldName];
            if (_.contains(this.MAIL_WIDGETS, fieldInfo.widget)) {
                this.mailFields[fieldInfo.widget] = fieldName;
                fieldInfo.__no_fetch = true;
            }
        }
        this.rendererParams.activeActions = this.controllerParams.activeActions;
        this.rendererParams.mailFields = this.mailFields;
    },
});

});
