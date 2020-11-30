odoo.define('base_setup.QRCodeAction', function (require) {
    "use strict";

    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');

    const QRModalAction = AbstractAction.extend({
        template: 'base_setup_qr_code',
        xmlDependencies: ['/base_setup/static/src/xml/qr_modal_template.xml'],

        init(parent, action) {
            this._super(...arguments);
            this.url = _.str.sprintf("/report/barcode/?type=QR&value=%s&width=256&height=256&humanreadable=1", action.params.url);
            this.appName = _.str.sprintf(action.appName);
        },
    });

    core.action_registry.add('qr_code_modal', QRModalAction);
});
