odoo.define('project.portalChatter', function (require) {
    "use strict";
    
    var Chatter = require('mail.Chatter');
    var ProjectPortalThreadField = require('project.ThreadField');
    
    /**
     * Handle custom mail field 'portal_project_mail_thread' on initialization of the chatter.
     */
    Chatter.include({
        /**
         * @override
         * @param {Object} record 
         * @param {Object} mailFields 
         * @param {Object} options 
         * @param {string} [options.viewType=record.viewType] current viewType in
         *   which the chatter is instantiated
         */
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
