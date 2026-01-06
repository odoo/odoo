import { registry } from "@web/core/registry";
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('website_hr_recruitment_skills_tour', {
    steps: () => [{
        content: "Select Job",
        trigger: `.oe_website_jobs h3:contains(Guru)`,
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Apply",
        trigger: ".js_hr_recruitment a:contains(Apply)",
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Complete name",
        trigger: "input[name=partner_name]",
        run: `edit John Smith`,
    }, {
        content: "Complete Email",
        trigger: "input[name=email_from]",
        run: `edit john@smith.com`,
    }, {
        content: "Complete phone number",
        trigger: "input[name=partner_phone]",
        run: `edit 118.218`,
    }, {
        content: "Complete LinkedIn profile",
        trigger: "input[name=linkedin_profile]",
        run: `edit linkedin.com/in/john-smith`,
    }, {
        content: "Complete Skills",
        trigger: "input[name=skill_ids]",
        run: "click"
    }, {
        content: "Send the form",
        trigger: ".s_website_form_send",
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Check the form is submitted without errors",
        trigger: "#jobs_thankyou h1:contains('Congratulations')",
    }],
});

registerWebsitePreviewTour('website_hr_recruitment_skills_tour_edit_form', {}, () => [
    stepUtils.waitIframeIsReady(),
{
    content: 'Go to the Guru job page',
    trigger: ':iframe a[href*="guru"]',
    run: "click",
}, {
    content: 'Go to the Guru job form',
    trigger: ':iframe a[href*="apply"]',
    run: "click",
}, {
    content: 'Check if the Guru form is present',
    trigger: ':iframe form',
    run: "click",
},
...clickOnEditAndWaitEditMode(),
{
    content: "Click on the form to select it",
    trigger: ":iframe .s_website_form form",
    run: "click",
},
{
    content: "Click on add field button",
    trigger: ".options-container-header button:contains('+ Field')",
    run: "click",
},
{
    content: "Select field type as Skills",
    trigger: "[data-container-title=Field] [data-action-value=applicant_skill_ids]:not(:visible)",
    run: "click",
},
{
    content: "Enable the first skill in the list",
    trigger: "[data-container-title=Field] .o_we_table_wrapper input[type='checkbox']",
    run: "click",
},
...clickOnSave(),
{
    content: "wait for the form values are patched",
    trigger: ":iframe form input[name=partner_name]:value(admin)",
},
{
    content: 'Go back to /jobs page after save',
    trigger: ":iframe nav a[href='/jobs']",
    run: "click",
}]);
