import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('mailing_activities_split', {
    url: '/odoo',
    steps: () => [
        {
            content: 'Open Activity Systray',
            trigger: '.o-mail-ActivityMenu-counter',
            run: "click",
        }, {
            content: 'Open Email Activities',
            trigger: '.o-mail-ActivityGroup:contains("Email Marketing")',
            run: "click",
        }, {
            content: 'Open Email Marketing record in the kanban view',
            trigger: '.o_list_renderer .o_data_cell:contains("New Email!")',
        },
        {
            content: "SMS Marketing record should not appear in this view",
            trigger: "body:not(:has(.o_list_renderer .o_data_cell:contains(New SMS!)))",
        },
        {
            content: 'Open Activity Systray',
            trigger: '.o-mail-ActivityMenu-counter',
            run: "click",
        }, {
            content: 'Open SMS Activities',
            trigger: '.o-mail-ActivityGroup:contains("SMS Marketing")',
            run: "click",
        }, {
            content: 'Open SMS Marketing record in the kanban view',
            trigger: '.o_list_renderer .o_data_cell:contains("New SMS!")',
        },
        {
            content: "Email Marketing record should not appear in this view",
            trigger: "body:not(:has(.o_list_renderer .o_data_cell:contains(New Email!)))",
        },
    ],
});
