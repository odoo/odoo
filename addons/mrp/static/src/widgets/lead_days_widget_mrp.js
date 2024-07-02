/** @odoo-module */

import { registry } from "@web/core/registry";
import { jsonPopOver, PopOverLeadDays } from "@stock/widgets/json_widget";

export class PopOverLeadDaysMrp extends PopOverLeadDays {
    static template = "mrp.mrpLeadDays";
}

export const popOverLeadDaysMrp = {
    ...jsonPopOver,
    component: PopOverLeadDaysMrp,
};
registry.category("fields").add("lead_days_widget_mrp", popOverLeadDaysMrp);
