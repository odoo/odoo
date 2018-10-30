odoo.define('project.MailBasicView', function (require) {
    "use strict";
    
    var BasicView = require('web.BasicView');

    /**
     * Adds custom mail widget 'portal_project_mail_thread' to the list of mail widgets.
     */
    BasicView.include({
        MAIL_WIDGETS: BasicView.prototype.MAIL_WIDGETS.concat(['portal_project_mail_thread']),
    });
    
    });
