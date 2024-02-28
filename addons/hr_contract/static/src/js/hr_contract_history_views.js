/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { HrContractHistoryListController } from "./hr_contract_history_list_controller";

export const HrContractHistoryView = {
    ...listView,
    Controller: HrContractHistoryListController,
}

registry.category("views").add('hr_contract_history_list', HrContractHistoryView);
