odoo.define('mail.BasicView', function (require) {
"use strict";

var BasicView = require('web.BasicView');

var mailWidgets = ['mail_followers', 'mail_thread', 'mail_activity', 'kanban_activity'];

BasicView.include({
    init: function () {
        this.mailFields = {};
        this._super.apply(this, arguments);
        this.rendererParams.activeActions = this.controllerParams.activeActions;
        this.rendererParams.mailFields = this.mailFields;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {Object} field - the field properties
     * @param {Object} attrs - the field attributes (from the xml)
     */
    _processField: function (field, attrs) {
        if (_.contains(mailWidgets, attrs.widget)) {
            this.mailFields[attrs.widget] = attrs.name;
            field.__no_fetch = true;
        }
        this._super.apply(this, arguments);
    },
});

});
