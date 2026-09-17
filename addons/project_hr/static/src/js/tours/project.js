/** @odoo-module native */
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import "@project/js/tours/project";

patch(registry.category("web_tour.tours").get("project_tour"), {
    steps() {
        return super.steps().map((step) =>
            typeof step.trigger === "string" && step.trigger.includes("user_ids")
                ? {
                      ...step,
                      trigger: step.trigger.replaceAll("user_ids", "employee_ids"),
                  }
                : step,
        );
    },
});
