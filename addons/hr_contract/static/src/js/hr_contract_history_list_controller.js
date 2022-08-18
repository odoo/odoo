/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";

export class HrContractHistoryListController extends ListController {
    setup() {
        super.setup();
        this.actionService = useService('action');
    }

    /**
     * @override
     */
    async createRecord({ group } = {}) {
        this.actionService.doAction({
            name: this.env._t('New Employee'),
            type: 'ir.actions.act_window',
            res_model: 'hr.employee',
            views: [[false, 'form']],
            view_mode: 'form',
        });
    }
}
