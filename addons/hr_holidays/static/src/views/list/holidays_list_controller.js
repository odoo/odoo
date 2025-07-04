import { useService } from "@web/core/utils/hooks";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { ListController } from "@web/views/list/list_controller";
import { useSubEnv } from "@odoo/owl";

export class HolidaysListController extends ListController {
    static template = "hr_holidays.HolidaysListView";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.onClickViewButton = this.env.onClickViewButton;

        useSubEnv({
            onClickViewButton: (params) => this.handleViewButtonClick(params),
        });
    }

    get actionFilters() {
        return {
            action_approve: (record) => record.data.can_approve || record.data.can_validate,
            action_refuse: (record) => record.data.can_refuse,
        };
    }

    handleViewButtonClick(params) {
        const actionName = params.clickParams.name;
        const filter = this.actionFilters[actionName];
        if (filter) {
            const eligibleRecords = this.model.root.selection.filter(filter);
            if (eligibleRecords.length) {
                this.executeAction(actionName, eligibleRecords);
            } else {
                this.onClickViewButton(params);
            }
        }
    }

    displayButton(button) {
        const { selection } = this.model.root;
        if (!selection.length) {
            return false;
        }
        const filter = this.actionFilters[button.clickParams.name];
        return filter ? selection.some(filter) : false;
    }

    async executeAction(functionName, records) {
        await this.orm.call(
            this.props.resModel,
            functionName,
            [records.map((record) => record.resId)],
        );
        await this.actionService.doAction({
            type: "ir.actions.client",
            tag: "soft_reload",
        });
    }
}

export const holidaysListView = {
    ...listView,
    Controller: HolidaysListController,
};

registry.category('views').add('hr_holidays_payslip_list', holidaysListView)
