import { registry } from "@web/core/registry";
import "@industry_fsm/../tests/tours/fsm_task_form_tour";
import { patch } from "@web/core/utils/patch";

patch(registry.category("web_tour.tours").get("fsm_task_form_tour"), {
    steps() {
        const originalSteps = super.steps();
        const industryFsmReport = originalSteps.findIndex((step) => step.id === "validate_customer");
        originalSteps.splice(industryFsmReport  + 1, 0, {
            content: 'Click on Worksheet Template Dropdown',
            trigger: 'div[name="worksheet_template_id"] input',
        },
        {
            content: 'Enter name for new worksheet in Many2One field',
            trigger: 'div[name="worksheet_template_id"] input',
            run: 'fill Worksheet-1'
        },
        {
            content: 'Click on Create and Edit',
            trigger: 'a.dropdown-item:contains("Create and edit...")',
            run: 'click',
        },
        {
            content: 'Click on company Dropdown',
            trigger: '.modal div[name="company_id"] input',
            run: 'click',
        },
        {
            content: 'Select the company from the wizard',
            trigger: '.ui-autocomplete > li > a:not(:has(i.fa))',
            run: 'click',
        },
        {
            content: 'Click on save and close',
            trigger: 'button[special="save"]',
            run: 'click',
        }, {
            trigger: 'body:not(.modal-open)',
        });
        return originalSteps;
    }
});
