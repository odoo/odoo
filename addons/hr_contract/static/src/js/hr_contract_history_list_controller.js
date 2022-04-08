/** @odoo-module **/

import ListController from "web.ListController";
import { _lt } from 'web.core';

export const HrContractHistoryListController = ListController.extend({

    /**
     * @override
     */
    _onCreateRecord(ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.do_action({
            name: _lt('New Employee'),
            type: 'ir.actions.act_window',
            res_model: 'hr.employee',
            views: [[false, 'form']],
            view_mode: 'form',
        });
    },
});
