/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('mailing_activities_split', {
    test: true,
    url: '/web',
    steps: () => [
        {
            content: 'Open Activity Systray',
            trigger: '.o-mail-ActivityMenu-counter',
        }, {
            content: 'Open Email Activities',
            trigger: '.o-mail-ActivityGroup:contains("Email Marketing")',
        }, {
            content: 'Open Email Marketing record in the kanban view',
            trigger: '.o_list_renderer .o_data_cell:contains("New Email!")',
            run: () => {
                if ($('.o_list_renderer .o_data_cell:contains("New SMS!")').length !== 0) {
                    console.error('SMS Marketing record should not appear in this view');
                }
            },
        }, {
            content: 'Open Activity Systray',
            trigger: '.o-mail-ActivityMenu-counter',
        }, {
            content: 'Open SMS Activities',
            trigger: '.o-mail-ActivityGroup:contains("SMS Marketing")',
        }, {
            content: 'Open SMS Marketing record in the kanban view',
            trigger: '.o_list_renderer .o_data_cell:contains("New SMS!")',
            run: () => {
                if ($('.o_list_renderer .o_data_cell:contains("New Email!")').length !== 0) {
                    console.error('Email Marketing record should not appear in this view');
                }
            },
        }
    ],
});
