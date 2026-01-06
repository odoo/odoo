import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import "@website_hr_recruitment/../tests/tours/website_hr_recruitment";

patch(registry.category("web_tour.tours").get("website_hr_recruitment_tour_edit_form"), {
    steps() {
        const originalSteps = super.steps();
        const editStepIndex = originalSteps.findIndex(
            (step) => step.id === "set_fake_job_id_default"
        );
        originalSteps.splice(editStepIndex, 0, {
            content: "Click on the form to select it",
            trigger: ":iframe .s_website_form form",
            run: "click",
        }, {
            content: "Click on add field button",
            trigger: ".options-container-header button:contains('+ Field')",
            run: "click",
        }, {
            content: "Select field type as Skills",
            trigger: "[data-container-title=Field] [data-action-value=applicant_skill_ids]:not(:visible)",
            run: "click",
        }, {
            content: "Enable the first skill type in the list",
            trigger: "[data-container-title=Field] .o_we_table_wrapper input[type='checkbox']",
            run: "click",
        });
        return originalSteps;
    },
});

patch(registry.category("web_tour.tours").get("website_hr_recruitment_tour"), {
    steps() {
        const originalSteps = super.steps();
        // The skills field has only been added on the Guru job form.
        const sendFormStepIndex = originalSteps.findIndex((step) => step.id === "send_form_guru");
        originalSteps.splice(sendFormStepIndex, 0, {
            content: "Complete Skills",
            trigger: "input[name=skill_ids]",
            run: "click",
        });
        return originalSteps;
    },
});
