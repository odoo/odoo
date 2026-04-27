/**
 * Adapt the steps related to sign/send feature of the fsm report to avoid duplicate steps between industry_fsm_report and industry_fsm_sale modules
 */

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

import "@industry_fsm/js/tours/industry_fsm_tour";

patch(registry.category("web_tour.tours").get("industry_fsm_tour"), {
    steps() {
        const originalSteps = super.steps();
        const fsmStartStepIndex = originalSteps.findIndex((step) => step.id === "industry_fsm_sale_sign_send_start");
        const fsmStopStepIndex = originalSteps.findIndex((step) => step.id === "industry_fsm_sale_sign_send_end");
        originalSteps.splice(fsmStartStepIndex, fsmStopStepIndex - fsmStartStepIndex + 1); // Remove duplicate steps from industry_fsm_sale
        return originalSteps;
    },
});
