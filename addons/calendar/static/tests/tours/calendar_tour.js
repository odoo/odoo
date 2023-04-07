/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";

    const todayDate = function() {
        let now = new Date();
        let year = now.getFullYear();
        let month = String(now.getMonth() + 1).padStart(2, '0');
        let day = String(now.getDate()).padStart(2, '0');

        return `${month}/${day}/${year} 10:00:00`;
    };

    registry.category("web_tour.tours").add('calendar_appointments_hour_tour', {
        url: '/web',
        test: true,
        steps: [stepUtils.showAppsMenuItem(),
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
            trigger: '#name_0',
            content: 'Give a name to the new event',
            run: 'text TEST EVENT',
        },
        {
            trigger: '#start_0',
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
    ]});
