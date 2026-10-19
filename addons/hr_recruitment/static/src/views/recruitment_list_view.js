import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { RecruitmentActionHelper } from "@hr_recruitment/views/recruitment_helper_view";
import { RecruitmentListController } from "@hr_recruitment/views/recruitment_list_controller";

export class RecruitmentListRenderer extends ListRenderer {
    static template = "hr_recruitment.RecruitmentListRenderer";
    static components = {
        ...ListRenderer.components,
        RecruitmentActionHelper,
    };
}

export const RecruitmentListView = {
    ...listView,
    Controller: RecruitmentListController,
    Renderer: RecruitmentListRenderer,
};

registry.category("views").add("recruitment_list_view", RecruitmentListView);
