/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const enterEditMode = [{
    content: "Select the contact us form by clicking on an input field",
    trigger: "iframe #wrap.o_editable section.s_website_form",
    extra_trigger: "iframe body.editor_enable",
}, {
    content: "Verify that the form editor appeared",
    trigger: '.o_we_customize_panel .snippet-option-WebsiteFormEditor',
    run: () => null,
}];

const websiteFormNoProject = [
    ...enterEditMode,
{
    content: "Open the action select",
    trigger: `we-select:has(we-button:contains("Send an E-mail")) we-toggler`,
}, {
    content: "Click on the option",
    trigger: `we-select we-button:contains("Create a Task")`,
}, {
    content: "Click on the 'Cancel' button in the dialog pop-up",
    trigger: `div.modal-dialog div.modal-content footer.modal-footer button:contains("Cancel")`,
    timeout: 3000,  // needs a timeout otherwise it fails in this step
}, {
    content: "Open the action select again",
    trigger: `we-select:has(we-button:contains("Send an E-mail")) we-toggler`,
}, {
    content: "Click on the option again",
    trigger: `we-select we-button:contains("Create a Task")`,
}, {
    content: "Click on the 'Create Project' button in the dialog pop-up",
    trigger: `div.modal-dialog div.modal-content footer.modal-footer button:contains("Create Project")`,
    timeout: 3000,  // needs a timeout otherwise it fails in this step
}, {
    content: "Check that we are inside the project form view",
    trigger: 'body:has(.o_form_view)',
}];

wTourUtils.registerWebsitePreviewTour('website_form_no_project_tour', {
    test: true,
    edition: true,
    url: '/contactus',
}, () => websiteFormNoProject);

const formErrorCreateProject = [
    ...enterEditMode,
{
    content: "Open the action select",
    trigger: `we-select:has(we-button:contains("Send an E-mail")) we-toggler`,
}, {
    content: "Click on the option",
    trigger: `we-select we-button:contains("Create a Task")`,
}, {
    content: "Save the page",
    trigger: 'button[data-action="save"]',
    extra_trigger: `we-select:has(we-button:contains("test project")) we-toggler`,
}, {
    content: 'Wait for reload',
    trigger: 'body:not(.editor_enable)',
}];

wTourUtils.registerWebsitePreviewTour('website_form_error_create_project', {
    test: true,
    edition: true,
    url: '/contactus',
}, () => formErrorCreateProject);
