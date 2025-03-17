import { useService } from "@web/core/utils/hooks";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { ListController } from "@web/views/list/list_controller";
import { _t } from "@web/core/l10n/translation";

export class HolidaysListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();

        if (this.model.root.selection.every((record) => record.data.can_approve)) {
            menuItems.approve = {
                isAvailable: () => { return true;},
                sequence: 50,
                description: _t('Approve'),
                callback: async () => await this.launchAction('action_approve'),
            };
        }

        if (this.model.root.selection.every((record) => record.data.can_validate)) {
            menuItems.validate = {
                isAvailable: () => { return true; },
                sequence: 60,
                description: _t('Validate'),
                callback: async () => await this.launchAction('action_approve'),
            };
        }

        if (this.model.root.selection.every((record) => record.data.can_refuse)) {
            menuItems.refuse = {
                sequence: 70,
                description: _t('Refuse'),
                callback: async () => await this.launchAction('action_refuse'),
            };
        }

        return menuItems;
    }

    async launchAction(functionName) {
        await this.orm.call(
            this.props.resModel,
            functionName,
            [this.model.root.selection.map((a) => a.resId)],
        );
        await this.actionService.doAction({
            'type': 'ir.actions.client',
            'tag': 'soft_reload',
        });
    }

}
export const holidaysListView = {
    ...listView,
    Controller: HolidaysListController,
};

registry.category('views').add('hr_holidays_payslip_list', holidaysListView)
