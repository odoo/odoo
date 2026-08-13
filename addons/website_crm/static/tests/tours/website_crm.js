/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('website_crm_pre_tour', {
    url: '/contactus',
    edition: true,
}, () => [{
    content: "Select contact form",
    trigger: ":iframe #wrap.o_editable section.s_website_form",
    run: "click",
},
{
    trigger: "#oe_snippets .o_we_customize_snippet_btn.active",
},
{
    content: "Open action select",
    trigger: "we-select:has(we-button:contains('Create an Opportunity')) we-toggler",
    run: "click",
}, {
    content: "Select 'Create an Opportunity' as form action",
    trigger: "we-select we-button:contains('Create an Opportunity')",
    run: "click",
},
...clickOnSave(),
{
    content: "Ensure form model has changed and page reload is done after save",
    trigger: ":iframe section.s_website_form form[data-model_name='crm.lead']",
}]);

registry.category("web_tour.tours").add('website_crm_tour', {
    url: '/contactus',
    steps: () => [{
    content: "Complete name",
    trigger: "input[name=contact_name]",
    run: "edit John Smith",
}, {
    content: "Complete phone number",
    trigger: "input[name=phone]",
    run: "edit +32 485 118.218",
}, {
    content: "Complete Email",
    trigger: "input[name=email_from]",
    run: "edit john@smith.com",
}, {
    content: "Complete Company",
    trigger: "input[name=partner_name]",
    run: "edit Odoo S.A.",
}, {
    content: "Complete Subject",
    trigger: "input[name=name]",
    run: "edit Useless message",
}, {
    content: "Complete Subject",
    trigger: "textarea[name=description]",
    run: "edit ### TOUR DATA ###",
}, {
    content: "Send the form",
    trigger: ".s_website_form_send",
    run: "click",
    expectUnloadPage: true,
}, {
    content: "Check we were redirected to the success page",
    trigger: "#wrap:has(h1:contains('Thank You!'))",
}]});

registry.category("web_tour.tours").add('website_crm_catch_logged_partner_info_tour', {
    url: '/contactus',
    steps: () => [
{
    content: "Wait the form is patched with values before continue to edit it",
    trigger: "form#contactus_form input[name=partner_name]:value(yourcompany)",
},
{
    content: "Complete Subject",
    trigger: "input[name=name]",
    run: "edit Useless subject",
}, {
    content: "Complete Subject",
    trigger: "textarea[name=description]",
    run: "edit ### TOUR DATA PREFILL ###",
}, {
    content: "Send the form",
    trigger: ".s_website_form_send",
    run: "click",
    expectUnloadPage: true,
}, {
    content: "Check we were redirected to the success page",
    trigger: "#wrap:has(h1:contains('Thank You!'))",
}]});
