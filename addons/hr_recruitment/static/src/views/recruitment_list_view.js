import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { RecruitmentListController } from "@hr_recruitment/views/recruitment_list_controller";

export const RecruitmentListView = {
    ...listView,
    Controller: RecruitmentListController,
};

registry.category("views").add("recruitment_list_view", RecruitmentListView);
