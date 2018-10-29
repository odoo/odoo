odoo.define('project.portalChatter', function (require) {
    "use strict";
    
    var Chatter = require('mail.Chatter');
    var ProjectPortalThreadField = require('project.ThreadField');
    
    Chatter.include({
        initMailFields: function (record, mailFields, options) {
            this._super.apply(this, arguments);
            if (mailFields.portal_project_mail_thread) {
                this.fields.thread = new ProjectPortalThreadField(this, mailFields.portal_project_mail_thread, record, options);
                var fieldsInfo = record.fieldsInfo[options.viewType || record.viewType];
                var nodeOptions = fieldsInfo[mailFields.portal_project_mail_thread].options || {};
                this.hasLogButton = options.display_log_button || nodeOptions.display_log_button;
                this.postRefresh = nodeOptions.post_refresh || 'never';
            }
        },
    });
    
    });
