/** @odoo-module **/
import tour from 'web_tour.tour';

const todayDate = function() {
    let now = new Date();
    let year = now.getFullYear();
    let month = String(now.getMonth() + 1).padStart(2, '0');
    let day = String(now.getDate()).padStart(2, '0');

    return `${month}/${day}/${year} 10:00:00`;
};

tour.register('calendar_appointments_hour_tour', {
    url: '/web',
    test: true,
}, [
    tour.stepUtils.showAppsMenuItem(),
    {
        trigger: '.o_app[data-menu-xmlid="calendar.mail_menu_calendar"]',
        content: 'Open Calendar',
        run: 'click',
    },
    {
        trigger: '.o-calendar-button-new',
        content: 'Create a new event',
        run: 'click',
    },
    {
        trigger: '#name',
        content: 'Give a name to the new event',
        run: 'text TEST EVENT',
    },
    {
        trigger: '#start',
        content: 'Give a date to the new event',
        run: `text ${todayDate()}`,
    },
    {
        trigger: '.fa-cloud-upload',
        content: 'Save the new event',
        run: 'click',
    },
    {
        trigger: '.dropdown-item:contains("Calendar")',
        content: 'Go back to Calendar view',
        run: 'click',
    },
    {
        trigger: '.dropdown-toggle:contains("Week")',
        content: 'Click to change calendar view',
        run: 'click',
    },
    {
        trigger: '.dropdown-item:contains("Month")',
        content: 'Change the calendar view to Month',
        run: 'click',
    },
    {
        trigger: '.fc-day-header:contains("Monday")',
        content: 'Change the calendar view to week',
    },
    {
        trigger: '.fc-time:contains("10:00")',
        content: 'Check the time is properly displayed',
    },
    {
        trigger: '.o_event_title:contains("TEST EVENT")',
        content: 'Check the event title',
    },
]);

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

tour.register('test_calendar_decline_tour', {
    test: true,
},
[
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
        content: 'Wait declined status',
        trigger: '.o_attendee_status_declined',
    },
]);

tour.register('test_calendar_decline_with_everybody_filter_tour', {
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
        content: 'Select filter (everybody)',
        trigger: 'div[data-value="all"] input',
    },
    {
        content: 'Wait declined status',
        trigger: '.o_attendee_status_declined',
    },
]);
