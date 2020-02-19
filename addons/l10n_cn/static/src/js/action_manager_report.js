odoo.define('l10n_cn.ReportActionManager', function (require) {
"use strict";
/**
 * The purpose of this file is to check if cn2an is installed.
 */

const ActionManager = require('web.ActionManager');
const core = require('web.core');

const _t = core._t;

ActionManager.include({
    _executeReportAction: function (action, options) {
        if (action.xml_id && action.xml_id == "l10n_cn.account_voucher_cn") {
            this._rpc({
                method: 'check_cn2an',
                model: 'account.move',
            }).then(res => {
                if (!res) {
                    var msg = _t("Unable to find cn2an on this system. The \"amount in words\" won't be shown.") + '<br><br><a href="https://pypi.org/project/cn2an/" target="_blank">cn2an · PyPI</a>';
                    this.do_notify(_t('Voucher'), msg);
                }
            })
        }
        return this._super.apply(this, arguments);
    },
});

});
