odoo.define('calendar.calendar_tour', function (require) {
    "use strict";

    const tour = require('web_tour.tour');

    tour.register('test_calendar_delete_tour', {
        test: true,
    },
    [
        {
            content: 'Select filter (everybody)',
            trigger: 'div[data-value="all"] input',
        },
        {
            content: 'Click on the event (focus + waiting)',
            trigger: 'a .fc-content:contains("Test Event")',
            async run() {
                $('a .fc-content:contains("Test Event")').click();
                await new Promise((r) => setTimeout(r, 1000));
                $('a .fc-content:contains("Test Event")').click();
            }
        },
        {
            content: 'Delete the event',
            trigger: '.o_cw_popover_delete',
        },
        {
            content: 'Validate the deletion',
            trigger:'button:contains("Ok")',
            async run() {
                $('button:contains("Ok")').click();
                await new Promise((r) => setTimeout(r, 1000));
            }
        },
    ]);
});
