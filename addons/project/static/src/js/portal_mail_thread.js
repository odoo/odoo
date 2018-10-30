odoo.define('project.ThreadField', function (require) {
"use strict";

var field_registry = require('web.field_registry');
var ThreadField = require('mail.ThreadField');

/**
 * Adds custom options to thread widget upon starting the chatter.
 */
var ProjectThreadField = ThreadField.extend({
    /**
     * @override
     * @param  {Object} [options]
     * @return {Object} ThreadWidget
     */
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
