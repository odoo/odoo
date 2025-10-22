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

        // Store reference to original button click handler for fallback
        this.onClickViewButton = this.env.onClickViewButton;

        useSubEnv({
            onClickViewButton: (params) => this.handleViewButtonClick(params),
        });
    }

    /**
     * Returns permission filters for holiday/leave actions.
     * Each filter checks if a record has the required permissions for the specific action.
     */
    get actionFilters() {
        return {
            action_approve: (record) => record.data.can_approve || record.data.can_validate,
            action_refuse: (record) => record.data.can_refuse,
        };
    }

    /**
     * Intercepts button clicks to apply permission-based filtering for holiday actions.
     * For approve/refuse actions, only processes records that have the required permissions.
     * Falls back to original handler if no eligible records or for other actions.
     *
     * @param {Object} params - Button click parameters containing action details
     */
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
        } else {
            this.onClickViewButton(params);
        }
    }

    /**
     * Determines whether a button should be displayed based on current selection and permissions.
     * Only shows approve/refuse buttons if at least one selected record has the required permissions.
     *
     * @param {Object} button - Button configuration object
     * @returns {boolean} True if button should be displayed
     */
    displayButton(button) {
        const { selection } = this.model.root;
        if (!selection.length) {
            return false;
        }
        const filter = this.actionFilters[button.clickParams.name];
        return filter ? selection.some(filter) : false;
    }

    /**
     * Executes an action (approve/refuse) on the specified records and refreshes the view.
     *
     * @param {string} functionName - Name of the backend method to call
     * @param {Array} records - Array of record objects to process
     */
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
