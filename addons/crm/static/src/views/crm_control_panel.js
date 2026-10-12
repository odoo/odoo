import { ControlPanel } from "@web/search/control_panel/control_panel";
import { CrmBreadcrumbs } from "@crm/components/breadcrumbs/crm_breadcrumbs"

export class CrmControlPanel extends ControlPanel {
    static components = {
        ...ControlPanel.components,
        Breadcrumbs: CrmBreadcrumbs,
    };
};
