import { registry } from "@web/core/registry";

import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { AppraisalActionHelper } from "@hr_appraisal/views/appraisal_helper_view";

export class AppraisalListRenderer extends ListRenderer {
    static template = "hr_appraisal.AppraisalListRenderer";
    static components = {
        ...AppraisalListRenderer.components,
        AppraisalActionHelper,
    };
};

export const AppraisalListView = {
    ...listView,
    Renderer: AppraisalListRenderer,
};

registry.category("views").add("appraisal_list_view", AppraisalListView);
