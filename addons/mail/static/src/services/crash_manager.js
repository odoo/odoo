odoo.define('mail.CrashManager', function (require) {
    "use strict";

    const { CrashManager } = require('web.CrashManager');
    const { _lt } = require('web.core');

    CrashManager.include({
        /**
         * @override
         */
        init() {
            this._super.apply(this, arguments);
            this.odooExceptionTitleMap = Object.assign({}, this.odooExceptionTitleMap, {
                'odoo.addons.base.models.ir_mail_server.MailDeliveryException': _lt("MailDeliveryException")
            });
        },
    });

});
