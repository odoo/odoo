import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class HrActionHelper extends Component {
    static template = "hr.EmployeeActionHelper";
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.actionHelperService = useService("hr_action_helper");
        onWillStart(async () => {
            this.showActionHelper = await this.actionHelperService.showActionHelper();
        });
    }

    loadEmployeeScenario() {
        this.actionService.doAction("hr.action_hr_employee_load_demo_data");
    }
}
