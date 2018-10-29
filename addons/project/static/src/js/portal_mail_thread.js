odoo.define('project.ThreadField', function (require) {
"use strict";

var field_registry = require('web.field_registry');
var ThreadField = require('mail.ThreadField');

var ProjectThreadField = ThreadField.extend({
    createThreadWidget: function (options) {
        options = _.defaults({
            displayStars: false,
            displayDocumentLinks: false,
            displayAvatars: false,
            displayEmailIcons: false,
        }, options || {});
        return this._super.apply(this, [options]);
    }
});

field_registry.add('portal_project_mail_thread', ProjectThreadField);

return ProjectThreadField;
});
