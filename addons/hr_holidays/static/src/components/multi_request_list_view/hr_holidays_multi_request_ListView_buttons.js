import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class MultiTimeOffGenerationListController extends ListController {
    openMatchingJobApplicants() {
        const resModel = this.env.searchModel.resModel;
        if (resModel === "hr.leave") {
            this.actionService.doAction("hr_holidays.action_hr_leave_generate_multi_wizard");
        } else {
            this.actionService.doAction("hr_holidays.action_hr_leave_allocation_generate_multi_wizard");
        }
    }
}

const MultiTimeOffGenerationListView = {
    ...listView,
    Controller: MultiTimeOffGenerationListController,
    buttonTemplate: "hr_holidays.multi_request.ListView.buttons",
};

registry.category("views").add("hr_holidays_multi_request_tree", MultiTimeOffGenerationListView);
