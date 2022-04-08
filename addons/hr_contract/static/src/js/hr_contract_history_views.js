/** @odoo-module **/

import ListView from "web.ListView";
import viewRegistry from 'web.view_registry';
import { HrContractHistoryListController } from "./hr_contract_history_list_controller";

export const HrContractHistoryView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: HrContractHistoryListController,
    }),
});

viewRegistry.add('hr_contract_history_list', HrContractHistoryView);
