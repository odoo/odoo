import { registry } from "@web/core/registry";
import {
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

function setFormActionToCreateOpportunity() {
    return [
        {
            content: "Select contact form",
            trigger: ":iframe #wrap.o_editable section.s_website_form",
            run: "click",
        },
        {
            trigger: ".o-snippets-menu .o-snippets-tabs [data-name='customize'].active",
        },
        {
            content: "Open action select",
            trigger:
                ".o-snippets-menu [data-container-title='Block'] [data-label='Action'] .dropdown-toggle",
            run: "click",
        },
        {
            content: "Select 'Create an Opportunity' as form action",
            trigger: ".o_popover [data-action-id='selectAction']:contains('Create an Opportunity')",
            run: "click",
        },
    ];
}

registerWebsitePreviewTour(
    "website_crm_pre_tour",
    {
        url: "/contactus",
        edition: true,
    },
    () => [
        ...setFormActionToCreateOpportunity(),
        ...clickOnSave(),
        {
            content: "Ensure form model has changed and page reload is done after save",
            trigger: ":iframe section.s_website_form form[data-model_name='crm.lead']",
        },
    ]
);

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


registerWebsitePreviewTour(
    "website_crm_form_properties",
    {
        url: "/contactus",
        edition: true,
    },
    () => [
        ...setFormActionToCreateOpportunity(),
        {
            content: "Open Sales Team select",
            trigger:
                ".o-snippets-menu [data-container-title='Block'] [data-label='Sales Team'] .dropdown-toggle",
            run: "click",
        },
        {
            content: "Select 'Sales' as Sales Team",
            trigger: ".o_popover [data-action-id='addActionField']:contains(Test Sales Team)",
            run: "click",
        },
        {
            content: "Wait the form is patched with values before continue to edit it",
            trigger: ":iframe form#contactus_form input[name=team_id]:not(:visible)",
        },
        {
            content: "Add a new field to the form",
            trigger: "button:contains(+ Field)",
            run: "click",
        },
        {
            content: "Open field Type selector",
            trigger: "[data-container-title=Field] button#type_opt",
            run: "click",
        },
        {
            content: "Select a property field",
            trigger: ".o_popover [data-action-id=existingField]:contains(test property)",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Check that there is no traceback",
            trigger: "body:not(:has(.o_error_dialog))",
            run: "click",
        },
    ]
);
