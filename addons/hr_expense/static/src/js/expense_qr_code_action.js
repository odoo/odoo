odoo.define('hr_expense.qr_code_action', function (require) {
"use strict";

const AbstractAction = require('web.AbstractAction');
const core = require('web.core');
const config = require('web.config');

const QRModalAction = AbstractAction.extend({
    template: 'hr_expense_qr_code',
    xmlDependencies: ['/hr_expense/static/src/xml/expense_qr_modal_template.xml'],

    init: function(parent, action){
        this._super.apply(this, arguments);
        this.url = _.str.sprintf("/report/barcode/?type=QR&value=%s&width=256&height=256&humanreadable=1", action.params.url);
    },
});

core.action_registry.add('expense_qr_code_modal', QRModalAction);
});
