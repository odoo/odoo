/** @odoo-module */

import { queryAll } from "@odoo/hoot-dom";
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
            run: () => {
                if (queryAll('.o_list_renderer .o_data_cell:contains("New SMS!")').length !== 0) {
                    console.error('SMS Marketing record should not appear in this view');
                }
            },
        }, {
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
            run: () => {
                if (queryAll('.o_list_renderer .o_data_cell:contains("New Email!")').length !== 0) {
                    console.error('Email Marketing record should not appear in this view');
                }
            },
        }
    ],
});
