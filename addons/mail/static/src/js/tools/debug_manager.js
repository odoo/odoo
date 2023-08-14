odoo.define('mail.DebugManager.Backend', function (require) {
"use strict";

var core = require('web.core');
var DebugManager = require('web.DebugManager.Backend');

var _t = core._t;
/**
 * adds a new method available for the debug manager, called by the "Manage Messages" button.
 *
 */
DebugManager.include({
    getMailMessages: function () {
        var selectedIDs = this._controller.getSelectedIds();
        if (!selectedIDs.length) {
            console.warn(_t("No message available"));
            return;
        }
        this.do_action({
            res_model: 'mail.message',
            name: _t('Manage Messages'),
            views: [[false, 'list'], [false, 'form']],
            type: 'ir.actions.act_window',
            domain: [['res_id', '=', selectedIDs[0]], ['model', '=', this._controller.modelName]],
            context: {
                default_res_model: this._controller.modelName,
                default_res_id: selectedIDs[0],
            },
        });
    },
});

});
