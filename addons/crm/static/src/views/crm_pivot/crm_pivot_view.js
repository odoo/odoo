import { CrmControlPanel } from "@crm/views/crm_control_panel/crm_control_panel";
import { CrmPivotModel } from "@crm/views/crm_pivot/crm_pivot_model";
import { pivotView } from "@web/views/pivot/pivot_view";
import { registry } from "@web/core/registry";

export const crmPivotView = {
    ...pivotView,
    ControlPanel: CrmControlPanel,
    Model: CrmPivotModel,
}

registry.category("views").add("crm_pivot", crmPivotView);
