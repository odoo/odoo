odoo.define('project.MailBasicView', function (require) {
    "use strict";
    
    var BasicView = require('web.BasicView');
    
    BasicView.include({
        MAIL_WIDGETS: BasicView.prototype.MAIL_WIDGETS.concat(['portal_project_mail_thread']),
    });
    
    });
